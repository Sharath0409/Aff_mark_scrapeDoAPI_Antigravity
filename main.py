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
        topic = row['Topic']
        keyword = row['Keyword']
        row_index = row['row_index']
        
        # 4. Scrape Products
        product_urls = scraper.search_products(keyword)
        if not product_urls:
            raise ValueError("No products found for keyword.")
            
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
        published_url = publisher.publish_post(topic, html_content, labels=seo_labels)
        
        # 7. Update Google Sheets
        sheets.update_row_status(row_index, "Success", url=published_url)
        logger.info(f"Pipeline finished successfully for topic: {topic}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        # Update sheet with error
        # sheets.update_row_status(row_index, "Failed", error=str(e))

if __name__ == "__main__":
    main()
