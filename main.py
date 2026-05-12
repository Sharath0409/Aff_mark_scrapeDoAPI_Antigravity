import sys
from config.logger import get_logger
from config import settings
from core.sheets_manager import SheetsManager
from core.scraper import AmazonScraper
from core.content_generator import ContentGenerator
from core.blogger_publisher import BloggerPublisher
from core.notifier import EmailNotifier

logger = get_logger("main")

def main():
    logger.info("Starting Autonomous Affiliate Publisher Pipeline")
    
    # 1. Initialize Modules
    sheets = SheetsManager(settings.GOOGLE_SHEET_ID, settings.GCP_SERVICE_ACCOUNT)
    scraper = AmazonScraper()
    generator = ContentGenerator()
    publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
    notifier = EmailNotifier()
    
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
        keyword = row['Keyword']
        row_index = row['row_index']
        
        # 4. Scrape Products (with 3-attempt retry logic)
        import time
        max_retries = 3
        product_urls = []
        
        for attempt in range(1, max_retries + 1):
            logger.info(f"Searching Amazon (Attempt {attempt}/{max_retries}) for: {keyword}")
            product_urls = scraper.search_products(keyword)
            if product_urls:
                break
            if attempt < max_retries:
                logger.warning(f"No products found on attempt {attempt}. Retrying in 10 seconds...")
                time.sleep(10)
        
        if not product_urls:
            raise ValueError(f"No products found for keyword '{keyword}' after {max_retries} attempts.")
            
        products_data = []
        for url in product_urls[:3]:  # Top 3 products
            data = scraper.scrape_product_details(url)
            if data:
                products_data.append(data)
                
        # 5. Generate Content
        html_content = generator.generate_full_post(topic, keyword, products_data)
        
        # 5.5 Generate SEO Labels
        seo_labels = generator.generate_seo_tags(topic, keyword)
        category = row.get('Category', 'Review')
        if category not in seo_labels:
            seo_labels.append(category)
        
        # 6. Publish to Blogger
        # Sanitize title to help Blogger generate a cleaner slug
        clean_title = topic.strip()
        published_url, current_post_id = publisher.publish_post(clean_title, html_content, labels=seo_labels)
        
        # 7. Update Google Sheets
        sheets.update_row_status(row_index, "Success", url=published_url, post_id=current_post_id)
            
        logger.info(f"Pipeline finished successfully for topic: {topic}")
        
        # 8. Send Success Report
        notifier.send_report("Success", topic, f"Post published at: {published_url}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        # 9. Send Fatal Failure Report (after all retries failed)
        try:
            notifier.send_report("Failure", topic if 'topic' in locals() else "Unknown", str(e))
        except:
            pass

if __name__ == "__main__":
    main()
