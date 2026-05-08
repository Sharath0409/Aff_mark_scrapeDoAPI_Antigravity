import sys
from config.logger import get_logger
from config import settings
from core.sheets_manager import SheetsManager
from core.scraper import AmazonScraper
import json

logger = get_logger("test")

def main():
    logger.info("Testing Sheets & Scraper Pipeline")
    
    # 1. Init
    try:
        sheets = SheetsManager(settings.GOOGLE_SHEET_ID, settings.GCP_SERVICE_ACCOUNT)
    except Exception as e:
        logger.error(f"Failed to init Sheets: {e}")
        return

    # 2. Fetch pending row
    row = sheets.get_pending_row()
    if not row:
        logger.warning("No pending rows found in the sheet. Please add a row with Status 'Pending', Topic, and Keyword.")
        logger.info("Fallback: testing scraper with keyword 'gaming mouse'")
        keyword = "gaming mouse"
    else:
        logger.info(f"Successfully fetched row: {row}")
        keyword = row.get("Keyword", "gaming mouse")

    # 3. Scrape
    try:
        scraper = AmazonScraper()
        urls = scraper.search_products(keyword)
        logger.info(f"Found URLs: {urls}")
        
        if urls:
            details = scraper.scrape_product_details(urls[0])
            logger.info(f"First product details:\n{json.dumps(details, indent=2)}")
        else:
            logger.warning("No products found.")
    except Exception as e:
        logger.error(f"Failed to scrape: {e}")

if __name__ == "__main__":
    main()
