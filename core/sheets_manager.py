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
            parent_id_idx = headers.index("Parent Post ID") if "Parent Post ID" in headers else -1
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
                    "Category": row[category_idx] if len(row) > category_idx else "",
                    "Parent Post ID": row[parent_id_idx] if parent_id_idx != -1 and len(row) > parent_id_idx else ""
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
        
    def update_row_status(self, row_index, status, url="", error="", post_id=""):
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
                
            if post_id and "Post ID" in headers:
                updates.append({
                    "range": f"{self.sheet_name}!{col_letter(headers.index('Post ID'))}{row_index}",
                    "values": [[post_id]]
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

    def add_related_topics(self, topics, parent_post_id, category="Review"):
        """Append new topics to the sheet with status 'Pending'."""
        try:
            values = self.get_all_rows()
            if not values:
                return
            headers = values[0]
            
            new_rows = []
            for topic in topics:
                # Prepare a row matching headers length
                row_data = [""] * len(headers)
                if "Topic" in headers:
                    row_data[headers.index("Topic")] = topic
                if "Keyword" in headers:
                    # Use the topic as the keyword for now
                    row_data[headers.index("Keyword")] = topic
                if "Category" in headers:
                    row_data[headers.index("Category")] = category
                if "Status" in headers:
                    row_data[headers.index("Status")] = "Pending"
                if "Parent Post ID" in headers:
                    row_data[headers.index("Parent Post ID")] = parent_post_id
                new_rows.append(row_data)
                
            if new_rows:
                self.sheet.values().append(
                    spreadsheetId=self.sheet_id,
                    range=self.sheet_name,
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body={"values": new_rows}
                ).execute()
                logger.info(f"Successfully added {len(new_rows)} related topics to the sheet.")
        except Exception as e:
            logger.error(f"Failed to append related topics: {e}")

    def get_processed_topics(self):
        """Fetch all topics that have already been processed or published."""
        try:
            values = self.get_all_rows()
            if not values or len(values) < 2:
                return []
            
            headers = values[0]
            if "Topic" not in headers or "Status" not in headers:
                return []
                
            topic_idx = headers.index("Topic")
            status_idx = headers.index("Status")
            
            processed = []
            for row in values[1:]:
                status = row[status_idx].lower() if len(row) > status_idx else ""
                if status in ['success', 'published', 'skipped - duplicate topic']:
                    if len(row) > topic_idx:
                        processed.append(row[topic_idx])
            return processed
        except Exception as e:
            logger.error(f"Error getting processed topics from sheet: {e}")
            return []

    def update_dashboard_stats(self, status):
        """Update the 'Dashboard' sheet with execution statistics and live formulas."""
        dashboard_sheet = "Dashboard"
        try:
            # Read Dashboard data
            result = self.sheet.values().get(spreadsheetId=self.sheet_id, range=f"{dashboard_sheet}!A1:B10").execute()
            values = result.get('values', [])
            
            if not values:
                # Initialize Dashboard with interactive formulas
                init_values = [
                    ["Metric", "Count"],
                    ["Success", 0],
                    ["Failed", 0],
                    ["Skipped - Duplicate Topic", 0],
                    ["Total Runs", 0],
                    ["", ""],
                    ["Live Success Rate (%)", "=IF(B5>0, ROUND(B2/B5*100, 2), 0)"],
                    ["Total Published Articles", "=B2"]
                ]
                self.sheet.values().update(
                    spreadsheetId=self.sheet_id,
                    range=f"{dashboard_sheet}!A1:B8",
                    valueInputOption="USER_ENTERED", # Use USER_ENTERED to parse formulas
                    body={"values": init_values}
                ).execute()
                values = init_values

            metric_col = [row[0] for row in values]
            updates = []
            
            # 1. Increment specific status count
            if status in metric_col:
                idx = metric_col.index(status)
                current_count = int(values[idx][1]) if len(values[idx]) > 1 else 0
                updates.append({
                    "range": f"{dashboard_sheet}!B{idx+1}",
                    "values": [[current_count + 1]]
                })
            
            # 2. Always increment 'Total Runs'
            if "Total Runs" in metric_col:
                idx = metric_col.index("Total Runs")
                current_total = int(values[idx][1]) if len(values[idx]) > 1 else 0
                updates.append({
                    "range": f"{dashboard_sheet}!B{idx+1}",
                    "values": [[current_total + 1]]
                })

            for update in updates:
                self.sheet.values().update(
                    spreadsheetId=self.sheet_id,
                    range=update["range"],
                    valueInputOption="RAW",
                    body={"values": update["values"]}
                ).execute()
                
            logger.info(f"Dashboard updated with status: {status}")
        except Exception as e:
            logger.error(f"Failed to update dashboard stats: {e}")

    def log_execution(self, topic, status, url="", error="", model="gpt-4o", product_count=0):
        """Log the detailed execution history of a single row into 'Execution Logs' tab."""
        log_sheet = "Execution Logs"
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check for header initialization
            result = self.sheet.values().get(spreadsheetId=self.sheet_id, range=f"{log_sheet}!A1:G1").execute()
            if not result.get('values'):
                headers = [["Timestamp", "Topic", "Status", "Model", "Products", "URL", "Error Log"]]
                self.sheet.values().update(
                    spreadsheetId=self.sheet_id,
                    range=f"{log_sheet}!A1:G1",
                    valueInputOption="RAW",
                    body={"values": headers}
                ).execute()

            # Append log entry (Preserves full history, one row per execution)
            log_entry = [[timestamp, topic, status, model, product_count, url, error]]
            self.sheet.values().append(
                spreadsheetId=self.sheet_id,
                range=log_sheet,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": log_entry}
            ).execute()
            logger.info(f"Historical record added to '{log_sheet}' for: {topic}")
        except Exception as e:
            logger.error(f"Failed to save execution history: {e}")
