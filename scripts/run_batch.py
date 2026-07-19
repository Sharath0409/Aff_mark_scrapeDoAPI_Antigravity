#!/usr/bin/env python3
"""Batch process rows from Google Sheets for publishing."""

import sys
import os
import time
import argparse

# Set up import path to project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.logger import get_logger
from config import settings
from core.sheets_manager import SheetsManager
from core.scraper import AmazonScraper
from core.content_generator import ContentGenerator
from core.blogger_publisher import BloggerPublisher
from core.notifier import EmailNotifier
from core.internal_linker import InternalLinkManager
from core.pipeline import process_row_with_cleanup
from utils.image_optimizer import ImageOptimizer
from utils.image_uploader import BloggerCDNUploader

logger = get_logger("run_batch")


def main():
    parser = argparse.ArgumentParser(description="Batch process rows from Google Sheets")
    parser.add_argument("--start-row", type=int, default=79, help="Starting row number (default: 79)")
    parser.add_argument("--end-row", type=int, default=89, help="Ending row number (default: 89)")
    args = parser.parse_args()

    logger.info(f"Initializing Batch Publisher for Rows {args.start_row} to {args.end_row}")
    
    sheets = SheetsManager(settings.GOOGLE_SHEET_ID, settings.GCP_SERVICE_ACCOUNT)
    scraper = AmazonScraper()
    generator = ContentGenerator()
    publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
    notifier = EmailNotifier()
    link_manager = InternalLinkManager(publisher)
    optimizer = ImageOptimizer()
    uploader = BloggerCDNUploader(settings.GCP_SERVICE_ACCOUNT)
    
    rows = sheets.get_all_rows()
    if not rows or len(rows) < 2:
        logger.error("Empty or invalid Google Sheet.")
        return

    headers = rows[0]
    
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
    status_idx = headers.index("Status") if "Status" in headers else -1
    parent_id_idx = headers.index("Parent Post ID") if "Parent Post ID" in headers else -1
    
    if status_idx == -1:
        logger.error("No Status column found in the Google Sheet.")
        return

    start_row = args.start_row
    end_row = args.end_row
    
    success_count = 0
    fail_count = 0
    skipped_count = 0

    for row_idx in range(start_row, end_row + 1):
        if row_idx > len(rows):
            logger.warning(f"Row {row_idx} exceeds total row count in sheet ({len(rows)}). Stopping.")
            break
            
        row_data = rows[row_idx - 1]
        status = row_data[status_idx] if len(row_data) > status_idx else ""
        
        if status.lower() != 'pending':
            logger.info(f"Row {row_idx} is not Pending (Status: {status}). Skipping.")
            skipped_count += 1
            continue
            
        row_dict = {
            "row_index": row_idx,
            "Topic": row_data[topic_idx] if len(row_data) > topic_idx else "",
            "Keyword": row_data[keyword_idx] if len(row_data) > keyword_idx else "",
            "Category": row_data[category_idx] if len(row_data) > category_idx else "",
            "Parent Post ID": row_data[parent_id_idx] if parent_id_idx != -1 and len(row_data) > parent_id_idx else ""
        }
        
        try:
            success = process_row_with_cleanup(
                sheets, scraper, generator, publisher, link_manager, 
                optimizer, uploader, row_dict
            )
            if success:
                success_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            logger.error(f"Failed to process Row {row_idx}: {e}", exc_info=True)
            fail_count += 1
            try:
                sheets.update_row_status(row_idx, "Failed", error=str(e))
                sheets.update_dashboard_stats("Failed")
                sheets.log_execution(row_dict["Topic"], "Failed", error=str(e))
            except Exception as sheet_err:
                logger.error(f"Failed to write error to Google Sheet for Row {row_idx}: {sheet_err}")
                
        # Slower pace to avoid rate limits
        time.sleep(5)
        
    logger.info(f"Batch completed! Success: {success_count}, Failed: {fail_count}, Skipped: {skipped_count}")
    try:
        notifier.send_report(
            "Batch Run Summary", 
            f"Rows {start_row}-{end_row}", 
            f"Processed rows {start_row} to {end_row}.\nSuccesses: {success_count}\nFailures: {fail_count}\nSkipped: {skipped_count}"
        )
    except Exception as e:
        logger.error(f"Failed to send summary email: {e}")

if __name__ == "__main__":
    main()