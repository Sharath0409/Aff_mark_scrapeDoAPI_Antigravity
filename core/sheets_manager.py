from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json
import base64
from config.logger import get_logger

logger = get_logger(__name__)

class SheetsManager:
    def __init__(self, sheet_id, credentials_env_val, sheet_name="Sheet1"):
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        
        # Determine if credentials_env_val is a path or base64 string
        try:
            if credentials_env_val.endswith('.json'):
                self.creds = Credentials.from_service_account_file(credentials_env_val, scopes=self.scopes)
            else:
                # Assume base64 encoded JSON string
                padding = len(credentials_env_val) % 4
                if padding > 0:
                    credentials_env_val += '=' * (4 - padding)
                creds_json = json.loads(base64.b64decode(credentials_env_val).decode('utf-8'))
                self.creds = Credentials.from_service_account_info(creds_json, scopes=self.scopes)
            
            self.service = build('sheets', 'v4', credentials=self.creds)
            self.sheet = self.service.spreadsheets()
            logger.info("Successfully connected to Google Sheets API.")
        except Exception as e:
            logger.error(f"Failed to initialize SheetsManager: {e}")
            raise

    def get_all_rows(self):
        """Fetch all rows from the specified sheet."""
        try:
            result = self.sheet.values().get(spreadsheetId=self.sheet_id, range=self.sheet_name).execute()
            values = result.get('values', [])
            return values
        except Exception as e:
            logger.error(f"Error fetching sheet data: {e}")
            return []

    def get_pending_row(self):
        """Fetch the first row with Status == 'Pending'."""
        values = self.get_all_rows()
        if not values or len(values) < 2:
            return None

        headers = values[0]
        try:
            status_idx = headers.index("Status")
            topic_idx = headers.index("Topic")
            keyword_idx = headers.index("Keyword")
            category_idx = headers.index("Category")
        except ValueError as e:
            logger.error(f"Missing required columns in Google Sheet: {e}")
            return None

        for idx, row in enumerate(values[1:], start=2): # +2 because 0-indexed + header row
            status = row[status_idx] if len(row) > status_idx else ""
            if status.lower() == 'pending':
                logger.info(f"Found pending row at index {idx}.")
                return {
                    "row_index": idx,
                    "Topic": row[topic_idx] if len(row) > topic_idx else "",
                    "Keyword": row[keyword_idx] if len(row) > keyword_idx else "",
                    "Category": row[category_idx] if len(row) > category_idx else ""
                }
        return None
        
    def get_pending_count(self):
        """Get the number of pending rows remaining."""
        values = self.get_all_rows()
        if not values or len(values) < 2:
            return 0
            
        try:
            status_idx = values[0].index("Status")
        except ValueError:
            return 0

        count = sum(1 for row in values[1:] if len(row) > status_idx and row[status_idx].lower() == 'pending')
        logger.info(f"Total pending rows remaining: {count}")
        return count
        
    def update_row_status(self, row_index, status, url="", error=""):
        """Update the row with Success/Failed status, Date, URL, and Error Log."""
        try:
            # We need to update columns dynamically
            values = self.get_all_rows()
            if not values:
                return
            headers = values[0]
            
            # Helper to get Google Sheet column letter (e.g., 0 -> A, 1 -> B)
            def col_letter(idx):
                return chr(65 + idx)
            
            from datetime import datetime
            today_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            updates = []
            
            if "Status" in headers:
                updates.append({
                    "range": f"{self.sheet_name}!{col_letter(headers.index('Status'))}{row_index}",
                    "values": [[status]]
                })
                
            if status == "Success" and "Publish Date" in headers:
                updates.append({
                    "range": f"{self.sheet_name}!{col_letter(headers.index('Publish Date'))}{row_index}",
                    "values": [[today_date]]
                })
                
            if url and "Blog URL" in headers:
                updates.append({
                    "range": f"{self.sheet_name}!{col_letter(headers.index('Blog URL'))}{row_index}",
                    "values": [[url]]
                })
                
            if error and "Error Log" in headers:
                updates.append({
                    "range": f"{self.sheet_name}!{col_letter(headers.index('Error Log'))}{row_index}",
                    "values": [[error]]
                })

            for update in updates:
                self.sheet.values().update(
                    spreadsheetId=self.sheet_id,
                    range=update["range"],
                    valueInputOption="RAW",
                    body={"values": update["values"]}
                ).execute()

            logger.info(f"Successfully updated row {row_index} to status: {status}")
        except Exception as e:
            logger.error(f"Failed to update row {row_index}: {e}")
