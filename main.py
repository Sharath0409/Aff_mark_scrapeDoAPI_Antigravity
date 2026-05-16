import sys
import logging
from config.logger import get_logger
from config import settings
from core.sheets_manager import SheetsManager
from core.scraper import AmazonScraper
from core.content_generator import ContentGenerator
from core.blogger_publisher import BloggerPublisher
from core.notifier import EmailNotifier
from core.internal_linker import InternalLinkManager
from utils.text_cleaner import normalize_topic
from utils.image_engine import ImageEngine

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
    
    # Initialize GitHub-based Image Engine
    image_engine = ImageEngine(
        github_user=settings.GITHUB_USERNAME,
        github_repo=settings.GITHUB_REPO_NAME
    )
    
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
        category = row.get('Category', 'general')
        row_index = row['row_index']
        
        # 3.5 Refresh Post Corpus
        link_manager.refresh_corpus()
        
        # 3.6 Duplicate Detection Logic
        logger.info(f"Performing duplicate check for: {topic}")
        normalized_current = normalize_topic(topic)
        historical_sheet = sheets.get_processed_topics()
        historical_blogger = [p['title'] for p in link_manager.corpus]
        all_history = historical_sheet + historical_blogger
        
        is_duplicate = False
        for hist_title in all_history:
            if normalize_topic(hist_title) == normalized_current:
                is_duplicate = True
                break
        
        if is_duplicate:
            logger.warning(f"Topic '{topic}' is a duplicate. Skipping...")
            sheets.update_row_status(row_index, "Skipped - Duplicate Topic")
            return
        
        # 4. Scrape Products
        import time
        max_retries = 3
        product_urls = []
        
        for attempt in range(1, max_retries + 1):
            logger.info(f"Searching Amazon (Attempt {attempt}/{max_retries}) for: {keyword}")
            product_urls = scraper.search_products(keyword)
            if product_urls:
                break
            if attempt < max_retries:
                time.sleep(10)
        
        if not product_urls:
            raise ValueError(f"No products found for keyword '{keyword}'.")
            
        products_data = []
        for url in product_urls[:3]:
            data = scraper.scrape_product_details(url)
            if data:
                # --- IMAGE OPTIMIZATION (GitHub Pages Flow) ---
                raw_image_url = data.get('image_url')
                if raw_image_url:
                    optimized_url = image_engine.download_and_optimize(
                        raw_image_url, 
                        data.get('title', 'product'),
                        category=category
                    )
                    if optimized_url:
                        data['image_url'] = optimized_url
                # ---------------------------------------------
                products_data.append(data)
                
        # 5. Generate Content
        html_content = generator.generate_full_post(topic, keyword, products_data)
        seo_labels = generator.generate_seo_tags(topic, keyword)
        if category not in seo_labels:
            seo_labels.append(category)
        
        # 5.6 Internal Linking
        related_posts = link_manager.get_related_articles(topic, seo_labels, count=3)
        if related_posts:
            html_content = link_manager.inject_internal_links(html_content, related_posts)
            html_content = link_manager.add_related_section(html_content, related_posts)
        
        # 6. Publish to Blogger
        clean_title = topic.strip()
        published_url, current_post_id = publisher.publish_post(clean_title, html_content, labels=seo_labels)
        
        # 7. Update Google Sheets
        sheets.update_row_status(row_index, "Success", url=published_url, post_id=current_post_id)
            
        logger.info(f"Pipeline finished successfully: {topic}")
        notifier.send_report("Success", topic, f"Post published at: {published_url}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        try:
            notifier.send_report("Failure", topic if 'topic' in locals() else "Unknown", str(e))
        except:
            pass

if __name__ == "__main__":
    main()
