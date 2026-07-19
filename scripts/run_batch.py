import sys, os
import logging
import time

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
from utils.text_cleaner import normalize_topic
from utils.image_optimizer import ImageOptimizer
from utils.image_uploader import BloggerCDNUploader
from scripts.remove_h1_tags import BloggerH1Remover

logger = get_logger("run_batch")

def run_single_row(sheets, scraper, generator, publisher, link_manager, optimizer, uploader, row):
    topic = row['Topic']
    keyword = row['Keyword']
    category = row.get('Category', 'general')
    row_index = row['row_index']
    
    logger.info(f"--- STARTING PROCESS FOR ROW {row_index}: {topic} ---")
    
    # 1. Refresh Post Corpus
    link_manager.refresh_corpus()
    
    # 2. Duplicate Detection
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
        sheets.update_dashboard_stats("Skipped - Duplicate Topic")
        sheets.log_execution(topic, "Skipped - Duplicate Topic")
        return False

    # 3. Scrape Products
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
    for url in product_urls[:5]:
        data = scraper.scrape_product_details(url)
        if data:
            raw_image_url = data.get('image_url')
            if raw_image_url:
                logger.info(f"Processing image for: {data.get('title')}")
                temp_webp, img_w, img_h = optimizer.process_from_url(raw_image_url, data.get('title', 'product'))
                if temp_webp:
                    cdn_url = uploader.upload_to_google_cdn(temp_webp, bucket_name=settings.GCS_BUCKET_NAME)
                    if cdn_url:
                        data['image_url'] = cdn_url
                        data['image_width'] = img_w
                        data['image_height'] = img_h
            products_data.append(data)
            
    if not products_data:
        raise ValueError(f"Scraped details failed for all search results for: {keyword}")

    # 4. Generate Content
    html_content = generator.generate_full_post(topic, keyword, products_data)
    seo_labels = generator.generate_seo_tags(topic, keyword)
    if category not in seo_labels:
        seo_labels.append(category)
        
    # 5. Internal Linking
    related_posts = link_manager.get_related_articles(topic, seo_labels, count=3)
    if related_posts:
        html_content = link_manager.inject_internal_links(html_content, related_posts)
        html_content = link_manager.add_related_section(html_content, related_posts)
        
    # 6. Clean H1 tags before publishing
    h1_remover = BloggerH1Remover(dry_run=False)
    cleaned_content, _ = h1_remover.clean_post_h1(topic.strip(), html_content)
    
    # 7. Publish to Blogger
    clean_title = topic.strip()
    published_url, current_post_id = publisher.publish_post(clean_title, cleaned_content, labels=seo_labels)
    
    # 8. Update Google Sheets
    sheets.update_row_status(row_index, "Success", url=published_url, post_id=current_post_id, product_count=len(products_data))
    sheets.update_dashboard_stats("Success")
    sheets.log_execution(topic, "Success", url=published_url, product_count=len(products_data))
    
    logger.info(f"--- SUCCESS FOR ROW {row_index}: {topic} ---")
    return True

def main():
    logger.info("Initializing Batch Publisher for Rows 79 to 89")
    
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

    start_row = 79
    end_row = 89
    
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
            success = run_single_row(
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
                
        # Clean up local image files between runs
        optimizer.cleanup()
        
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
