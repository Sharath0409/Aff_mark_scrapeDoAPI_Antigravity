"""Main Pipeline - Autonomous Affiliate Publisher"""

import sys
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

logger = get_logger("main")


def main():
    logger.info("Starting Autonomous Affiliate Publisher Pipeline with GitHub Pages Hosting")
    
    # 1. Initialize Modules
    sheets = SheetsManager(settings.GOOGLE_SHEET_ID, settings.GCP_SERVICE_ACCOUNT)
    scraper = AmazonScraper()
    generator = ContentGenerator()
    publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
    notifier = EmailNotifier()
    link_manager = InternalLinkManager(publisher)
    
    # Initialize Optimizer and Native Uploader
    optimizer = ImageOptimizer()
    uploader = BloggerCDNUploader(settings.GCP_SERVICE_ACCOUNT)
    
    try:
        # 2. Check pending count & warn if necessary
        pending_count = sheets.get_pending_count()
        if pending_count <= 5:
            notifier.send_warning(pending_count)
            
        if pending_count == 0:
            logger.info("No pending rows found. Exiting.")
            sys.exit(0)
            
        # 3. Fetch next pending row
        row = sheets.get_pending_row()
        if not row:
            logger.info("No pending rows found. Pipeline finished.")
            return

        topic = row['Topic']
        row_index = row['row_index']
        
        # 4. Process row with guaranteed cleanup - returns success status
        success = process_row_with_cleanup(
            sheets, scraper, generator, publisher, link_manager,
            optimizer, uploader, row
        )
        
        if success:
            # Re-fetch the live URL from the sheet (written by pipeline)
            updated_row = sheets.get_all_rows()
            if updated_row and len(updated_row) > row_index:
                row_data = updated_row[row_index - 1]  # row_index is 1-based
                headers = updated_row[0]
                if "Blog URL" in headers:
                    published_url = row_data[headers.index("Blog URL")]
                else:
                    published_url = "URL not found in sheet"
            else:
                published_url = "Could not re-fetch from sheet"
            
            logger.info(f"Pipeline finished successfully for topic: {topic}")
            notifier.send_report("Success", topic, f"Post published at: {published_url}")
            print(f"\n✅ Pipeline completed successfully. Live URL: {published_url}")
        else:
            logger.info(f"Pipeline skipped for topic: {topic} (duplicate)")
            print(f"\n⏭️ Pipeline skipped (duplicate topic)")
         
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        if 'row' in locals() and row:
            row_index = row.get('row_index')
            topic = row.get('Topic', 'Unknown')
            if row_index:
                try:
                    sheets.update_row_status(row_index, "Failed", error=str(e), product_count=0)
                    sheets.update_dashboard_stats("Failed")
                    sheets.log_execution(topic, "Failed", error=str(e), product_count=0)
                except Exception as sheet_err:
                    logger.error(f"Failed to update sheet on pipeline failure: {sheet_err}")
        try:
            notifier.send_report("Failure", topic if 'topic' in locals() else "Unknown", str(e))
        except:
            pass
        print(f"\n❌ Pipeline FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()