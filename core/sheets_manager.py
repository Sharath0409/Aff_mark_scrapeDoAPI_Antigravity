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

    def _ensure_sheet_exists(self, sheet_name):
        """Check if a sheet exists, if not, create it."""
        try:
            spreadsheet = self.sheet.get(spreadsheetId=self.sheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            exists = any(s.get('properties', {}).get('title') == sheet_name for s in sheets)
            
            if not exists:
                logger.info(f"Sheet '{sheet_name}' not found. Creating it...")
                batch_update_request_body = {
                    'requests': [{
                        'addSheet': {
                            'properties': {
                                'title': sheet_name
                            }
                        }
                    }]
                }
                self.sheet.batchUpdate(
                    spreadsheetId=self.sheet_id,
                    body=batch_update_request_body
                ).execute()
                logger.info(f"Successfully created sheet: {sheet_name}")
            return True
        except Exception as e:
            logger.error(f"Error ensuring sheet exists ({sheet_name}): {e}")
            return False

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
            
            # Helper to find column index with fallbacks
            def find_col_idx(col_name, fallbacks, default):
                if col_name in headers:
                    return headers.index(col_name)
                for fallback in fallbacks:
                    if fallback in headers:
                        return headers.index(fallback)
                return default

            topic_idx = find_col_idx("Topic", ["Column 1"], 0)
            keyword_idx = find_col_idx("Keyword", ["Column 2"], 1)
            category_idx = find_col_idx("Category", ["Column 3"], 2)
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
        
    def update_row_status(self, row_index, status, url="", error="", post_id="", product_count=None):
        """Update the row with Success/Failed status, Date, URL, Error Log, and Product Count."""
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

            if product_count is not None and "Product Count" in headers:
                updates.append({
                    "range": f"{self.sheet_name}!{col_letter(headers.index('Product Count'))}{row_index}",
                    "values": [[product_count]]
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
                elif "Column 1" in headers:
                    row_data[headers.index("Column 1")] = topic
                else:
                    row_data[0] = topic
                    
                if "Keyword" in headers:
                    # Use the topic as the keyword for now
                    row_data[headers.index("Keyword")] = topic
                elif "Column 2" in headers:
                    row_data[headers.index("Column 2")] = topic
                else:
                    row_data[1] = topic
                    
                if "Category" in headers:
                    row_data[headers.index("Category")] = category
                elif "Column 3" in headers:
                    row_data[headers.index("Column 3")] = category
                else:
                    row_data[2] = category
                    
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
            if "Status" not in headers:
                return []
                
            status_idx = headers.index("Status")
            
            if "Topic" in headers:
                topic_idx = headers.index("Topic")
            elif "Column 1" in headers:
                topic_idx = headers.index("Column 1")
            else:
                topic_idx = 0
            
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
            self._ensure_sheet_exists(dashboard_sheet)
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
                
                # Initialize the filter section for status-based row display
                self._initialize_dashboard_filter()

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

    def _initialize_dashboard_filter(self):
        """Initialize the filter section on the Dashboard sheet for status-based row display."""
        dashboard_sheet = "Dashboard"
        try:
            # Add filter helper section starting at column D
            filter_section = [
                ["", ""],  # Empty row for spacing
                ["Select Status to View Rows:", ""],
                ["Status Filter:", "Success"],  # D3: User selects status here
                ["", ""],
                ["Filtered Results for Status:"],
                ["Topic", "Keyword", "Category", "Status", "Blog URL", "Post ID", "Error Log"]
            ]
            
            self.sheet.values().update(
                spreadsheetId=self.sheet_id,
                range=f"{dashboard_sheet}!D1:E10",
                valueInputOption="RAW",
                body={"values": filter_section}
            ).execute()
            logger.info("Dashboard filter section initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize dashboard filter: {e}")

    def get_rows_by_status(self, target_status):
        """Fetch all rows from the main sheet that match a specific status."""
        try:
            values = self.get_all_rows()
            if not values or len(values) < 2:
                return []
            
            headers = values[0]
            if "Status" not in headers:
                return []
            
            status_idx = headers.index("Status")
            
            # Get indices for all relevant columns
            column_indices = {}
            for col_name in ["Topic", "Keyword", "Category", "Blog URL", "Post ID", "Error Log"]:
                if col_name in headers:
                    column_indices[col_name] = headers.index(col_name)
            
            matching_rows = [headers]  # Start with headers
            for row in values[1:]:
                row_status = row[status_idx].strip() if len(row) > status_idx else ""
                if row_status.lower() == target_status.lower():
                    # Build a row with only relevant columns
                    filtered_row = []
                    for col_name in ["Topic", "Keyword", "Category", "Status", "Blog URL", "Post ID", "Error Log"]:
                        if col_name in column_indices:
                            col_idx = column_indices[col_name]
                            filtered_row.append(row[col_idx] if len(row) > col_idx else "")
                        elif col_name == "Status":
                            filtered_row.append(row_status)
                    matching_rows.append(filtered_row)
            
            logger.info(f"Found {len(matching_rows) - 1} rows with status: {target_status}")
            return matching_rows
        except Exception as e:
            logger.error(f"Error fetching rows by status '{target_status}': {e}")
            return []

    def update_dashboard_filtered_results(self, status):
        """Update the Dashboard sheet with filtered rows for the selected status."""
        dashboard_sheet = "Dashboard"
        try:
            # Get rows matching the selected status
            matching_rows = self.get_rows_by_status(status)
            
            if not matching_rows:
                logger.warning(f"No rows found for status: {status}")
                return
            
            # Update the filter value indicator
            self.sheet.values().update(
                spreadsheetId=self.sheet_id,
                range=f"{dashboard_sheet}!E3",
                valueInputOption="RAW",
                body={"values": [[status]]}
            ).execute()
            
            # Clear previous results (up to 100 rows)
            clear_range = f"{dashboard_sheet}!D6:J105"
            self.sheet.values().clear(
                spreadsheetId=self.sheet_id,
                range=clear_range
            ).execute()
            
            # Write new filtered results starting at D6
            if len(matching_rows) > 1:  # More than just headers
                self.sheet.values().update(
                    spreadsheetId=self.sheet_id,
                    range=f"{dashboard_sheet}!D6",
                    valueInputOption="RAW",
                    body={"values": matching_rows}
                ).execute()
                logger.info(f"Dashboard filtered results updated for status: {status}")
            else:
                logger.info(f"No matching rows to display for status: {status}")
        except Exception as e:
            logger.error(f"Failed to update dashboard filtered results: {e}")

    def get_status_summary(self):
        """Get a summary of all unique statuses and their counts."""
        try:
            values = self.get_all_rows()
            if not values or len(values) < 2:
                return {}
            
            headers = values[0]
            if "Status" not in headers:
                return {}
            
            status_idx = headers.index("Status")
            status_counts = {}
            
            for row in values[1:]:
                row_status = row[status_idx].strip() if len(row) > status_idx else "Unknown"
                status_counts[row_status] = status_counts.get(row_status, 0) + 1
            
            logger.info(f"Status summary: {status_counts}")
            return status_counts
        except Exception as e:
            logger.error(f"Error getting status summary: {e}")
            return {}

    def display_rows_by_status(self, status):
        """
        Display all rows for a given status and update the dashboard.
        
        Args:
            status (str): The status to filter by (e.g., "Success", "Failed", "Pending")
        
        Returns:
            list: List of rows matching the status
        """
        matching_rows = self.get_rows_by_status(status)
        self.update_dashboard_filtered_results(status)
        return matching_rows

    def log_execution(self, topic, status, url="", error="", model="deepseek-v4-flash", product_count=0):
        """Log the detailed execution history of a single row into 'Execution Logs' tab."""
        log_sheet = "Execution Logs"
        try:
            self._ensure_sheet_exists(log_sheet)
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

    def log_review(self, topic, status, drift_summary="", url="", model="deepseek-v4-flash"):
        """Log the review action into 'Review Logs' tab."""
        log_sheet = "Review Logs"
        try:
            self._ensure_sheet_exists(log_sheet)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check for header initialization
            result = self.sheet.values().get(spreadsheetId=self.sheet_id, range=f"{log_sheet}!A1:F1").execute()
            if not result.get('values'):
                headers = [["Timestamp", "Topic", "Status", "Drift Summary", "Model", "URL"]]
                self.sheet.values().update(
                    spreadsheetId=self.sheet_id,
                    range=f"{log_sheet}!A1:F1",
                    valueInputOption="RAW",
                    body={"values": headers}
                ).execute()

            # Append log entry
            log_entry = [[timestamp, topic, status, drift_summary, model, url]]
            self.sheet.values().append(
                spreadsheetId=self.sheet_id,
                range=log_sheet,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": log_entry}
            ).execute()
            logger.info(f"Review record added to '{log_sheet}' for: {topic}")
        except Exception as e:
            logger.error(f"Failed to save review history: {e}")

    def get_recently_updated_posts(self, count=4):
        """Fetch the most recently updated/expanded posts from 'Review Logs' or 'Execution Logs'."""
        topics = []
        try:
            log_sheet = "Review Logs"
            result = self.sheet.values().get(spreadsheetId=self.sheet_id, range=f"{log_sheet}!A1:F500").execute()
            values = result.get('values', [])
            if values and len(values) > 1:
                headers = values[0]
                topic_idx = headers.index("Topic") if "Topic" in headers else 1
                url_idx = headers.index("URL") if "URL" in headers else 5
                for row in reversed(values[1:]):
                    if len(topics) >= count:
                        break
                    topic = row[topic_idx] if len(row) > topic_idx else ""
                    url = row[url_idx] if len(row) > url_idx else ""
                    if topic and topic not in [t["topic"] for t in topics]:
                        topics.append({"topic": topic, "url": url})
        except Exception as e:
            logger.warning(f"Could not fetch from Review Logs: {e}")

        if len(topics) < count:
            try:
                log_sheet = "Execution Logs"
                result = self.sheet.values().get(spreadsheetId=self.sheet_id, range=f"{log_sheet}!A1:G500").execute()
                values = result.get('values', [])
                if values and len(values) > 1:
                    headers = values[0]
                    topic_idx = headers.index("Topic") if "Topic" in headers else 1
                    url_idx = headers.index("URL") if "URL" in headers else 5
                    for row in reversed(values[1:]):
                        if len(topics) >= count:
                            break
                        topic = row[topic_idx] if len(row) > topic_idx else ""
                        url = row[url_idx] if len(row) > url_idx else ""
                        if topic and topic not in [t["topic"] for t in topics]:
                            topics.append({"topic": topic, "url": url})
            except Exception as e:
                logger.warning(f"Could not fetch from Execution Logs: {e}")

        return topics
