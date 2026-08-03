"""Shared Pipeline Module

Extracts common row processing logic used by main.py and run_batch.py.
Ensures optimizer cleanup happens via try/finally.
"""

import time
from typing import Dict, Any

from config.logger import get_logger
from config import settings
from core.sheets_manager import SheetsManager
from core.scraper import AmazonScraper
from core.content_generator import ContentGenerator
from core.blogger_publisher import BloggerPublisher
from core.internal_linker import InternalLinkManager
from utils.text_cleaner import normalize_topic
from utils.image_optimizer import ImageOptimizer
from utils.image_uploader import BloggerCDNUploader
from bs4 import BeautifulSoup

logger = get_logger("pipeline")


class BloggerH1Remover:
    """Remove/convert H1 tags in post content.
    
    - Deletes H1 if it matches the post title
    - Converts other H1 tags to H2
    """
    def __init__(self, dry_run=True):
        self.dry_run = dry_run

    def clean_post_h1(self, title, content):
        """Processes the H1 tags in the content. Returns (new_content, did_change)."""
        if not content or not content.strip():
            return content, False

        soup = BeautifulSoup(content, "html.parser")
        h1_tags = soup.find_all("h1")
        if not h1_tags:
            return content, False

        did_change = False
        normalized_title = title.strip().lower()

        for h1 in h1_tags:
            h1_text = h1.get_text().strip().lower()
            # If the H1 matches the post title, delete it
            if h1_text == normalized_title:
                h1.decompose()
                logger.info(f"  Deleted H1 matching title: '{h1_text}'")
                did_change = True
            else:
                # Rename the H1 tag to H2
                h1.name = "h2"
                logger.info(f"  Converted H1 to H2: '{h1_text}'")
                did_change = True

        return str(soup), did_change


def log_stage_start(stage_num, total_stages, stage_name):
    logger.info(f"Stage {stage_num}/{total_stages}: {stage_name}")
    print(f"--- STAGE {stage_num}/{total_stages}: {stage_name} ---")

def log_stage_pass(stage_num, total_stages, stage_name, details=""):
    logger.info(f"Stage {stage_num}/{total_stages} PASSED: {stage_name} {details}")
    print(f"Stage {stage_num}/{total_stages} PASSED: {stage_name} {details}")

def log_stage_fail(stage_num, total_stages, stage_name, error, blocking=True):
    logger.error(f"Stage {stage_num}/{total_stages} FAILED: {stage_name} - {error}")
    print(f"Stage {stage_num}/{total_stages} FAILED: {stage_name} - {error}")
    if blocking:
        logger.error(f"Blocking failure - workflow will exit")


def process_row(
    sheets: SheetsManager,
    scraper: AmazonScraper,
    generator: ContentGenerator,
    publisher: BloggerPublisher,
    link_manager: InternalLinkManager,
    optimizer: ImageOptimizer,
    uploader: BloggerCDNUploader,
    row: Dict[str, Any]
) -> bool:
    """Process a single row from the Google Sheet.
    
    Returns:
        True if successful, False if skipped (duplicate)
    """
    topic = row['Topic']
    keyword = row['Keyword']
    category = row.get('Category', 'general')
    row_index = row['row_index']
    
    TOTAL_STAGES = 10
    
    logger.info(f"--- STARTING COMMERCIAL PROCESS FOR ROW {row_index}: {topic} ---")
    
    # 1. Refresh Post Corpus
    log_stage_start(1, TOTAL_STAGES, "Refresh Post Corpus")
    link_manager.refresh_corpus()
    log_stage_pass(1, TOTAL_STAGES, "Refresh Post Corpus")
    
    # 2. Duplicate Detection
    log_stage_start(2, TOTAL_STAGES, "Duplicate Detection")
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
        log_stage_fail(2, TOTAL_STAGES, "Duplicate Detection", f"Topic '{topic}' is a duplicate", blocking=False)
        logger.warning(f"Topic '{topic}' is a duplicate. Skipping...")
        sheets.update_row_status(row_index, "Skipped - Duplicate Topic")
        sheets.update_dashboard_stats("Skipped - Duplicate Topic")
        sheets.log_execution(topic, "Skipped - Duplicate Topic")
        return False
    log_stage_pass(2, TOTAL_STAGES, "Duplicate Detection", "Not a duplicate")

    # 3. Scrape Products
    log_stage_start(3, TOTAL_STAGES, "Scrape Products")
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
        log_stage_fail(3, TOTAL_STAGES, "Scrape Products", f"No products found for keyword '{keyword}'")
        raise ValueError(f"No products found for keyword '{keyword}'.")
        
    products_data = []
    for url in product_urls[:7]:  # Support up to 7 products
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
        log_stage_fail(3, TOTAL_STAGES, "Scrape Products", f"Scraped details failed for all search results for: {keyword}")
        raise ValueError(f"Scraped details failed for all search results for: {keyword}")
    
    log_stage_pass(3, TOTAL_STAGES, "Scrape Products", f"Got {len(products_data)} products with images")

    # 4. Generate Content
    log_stage_start(4, TOTAL_STAGES, "Generate Full Post Content")
    html_content = generator.generate_full_post(topic, keyword, products_data)
    log_stage_pass(4, TOTAL_STAGES, "Generate Full Post Content", f"HTML length: {len(html_content)} chars")

    # 5. Monetization Validation (5-7 products, comparison table, etc.)
    log_stage_start(5, TOTAL_STAGES, "Monetization Validation")
    validation_passed, validation_details = generator.validate_monetization_structure(html_content, category, topic)
    if not validation_passed:
        log_stage_fail(5, TOTAL_STAGES, "Monetization Validation", f"Details: {validation_details}")
        sheets.update_row_status(row_index, "Needs Review", error=f"Monetization validation failed: {validation_details}")
        raise ValueError(f"Monetization validation failed: {validation_details}")
    log_stage_pass(5, TOTAL_STAGES, "Monetization Validation", f"Products: {validation_details.get('named_product_count', 0)}, Table cols: {validation_details.get('comparison_table_columns', 0)}")

    # 6. Internal Linking
    log_stage_start(6, TOTAL_STAGES, "Internal Linking")
    seo_labels = generator.generate_seo_tags(topic, keyword)
    if category not in seo_labels:
        seo_labels.append(category)
    related_posts = link_manager.get_related_articles(topic, seo_labels, count=3)
    if related_posts:
        html_content = link_manager.inject_internal_links(html_content, related_posts)
        html_content = link_manager.add_related_section(html_content, related_posts, category)
    log_stage_pass(6, TOTAL_STAGES, "Internal Linking", f"Injected {len(related_posts)} internal links")

    # 7. Clean H1 tags before publishing
    log_stage_start(7, TOTAL_STAGES, "Clean H1 Tags")
    h1_remover = BloggerH1Remover(dry_run=False)
    cleaned_content, _ = h1_remover.clean_post_h1(topic.strip(), html_content)
    log_stage_pass(7, TOTAL_STAGES, "Clean H1 Tags")

    # 8. Publish to Blogger as draft first
    log_stage_start(8, TOTAL_STAGES, "Publish as Draft to Blogger")
    clean_title = topic.strip()
    draft_url, current_post_id = publisher.publish_post_as_draft(clean_title, cleaned_content, labels=seo_labels)
    log_stage_pass(8, TOTAL_STAGES, "Publish as Draft to Blogger", f"Post ID: {current_post_id}, Draft URL: {draft_url}")

    # 9. Flip to published (LIVE)
    log_stage_start(9, TOTAL_STAGES, "Flip Draft to Published (LIVE)")
    try:
        publisher.publish_draft_post(current_post_id)
        log_stage_pass(9, TOTAL_STAGES, "Flip Draft to Published", f"Post ID: {current_post_id}")
    except Exception as e:
        log_stage_fail(9, TOTAL_STAGES, "Flip Draft to Published", str(e))
        raise

    # 10. Re-fetch post to get REAL live public URL, then update Sheets
    log_stage_start(10, TOTAL_STAGES, "Fetch Live URL & Update Sheets")
    try:
        live_post = publisher.get_post(current_post_id)
        live_url = live_post.get('url', '')
        if not live_url:
            # Fallback: construct URL from blog_id and post_id if needed
            live_url = f"https://www.remoteprostor.com/{current_post_id}"
        logger.info(f"Live post URL from Blogger API: {live_url}")
        
        sheets.update_row_status(row_index, "Success", url=live_url, post_id=current_post_id, product_count=len(products_data))
        sheets.update_dashboard_stats("Success")
        sheets.log_execution(topic, "Success", url=live_url, product_count=len(products_data))
        log_stage_pass(10, TOTAL_STAGES, "Fetch Live URL & Update Sheets", f"Live URL: {live_url}")
    except Exception as e:
        log_stage_fail(10, TOTAL_STAGES, "Fetch Live URL & Update Sheets", str(e))
        raise

    logger.info(f"--- SUCCESS FOR ROW {row_index}: {topic} ---")
    print(f"\n========================================")
    print(f"COMMERCIAL WORKFLOW COMPLETED SUCCESSFULLY")
    print(f"========================================")
    print(f"Topic: {topic}")
    print(f"Published URL: {live_url}")
    print(f"Post ID: {current_post_id}")
    print(f"Products: {len(products_data)}")
    print(f"========================================\n")
    return True


def process_row_with_cleanup(
    sheets: SheetsManager,
    scraper: AmazonScraper,
    generator: ContentGenerator,
    publisher: BloggerPublisher,
    link_manager: InternalLinkManager,
    optimizer: ImageOptimizer,
    uploader: BloggerCDNUploader,
    row: Dict[str, Any]
) -> bool:
    """Process a row with guaranteed optimizer cleanup via try/finally."""
    try:
        return process_row(sheets, scraper, generator, publisher, link_manager, optimizer, uploader, row)
    finally:
        optimizer.cleanup()