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
        html_content = link_manager.add_related_section(html_content, related_posts, category)
        
    # 6. Clean H1 tags before publishing
    h1_remover = BloggerH1Remover(dry_run=False)
    cleaned_content, _ = h1_remover.clean_post_h1(topic.strip(), html_content)
    
    # 7. Publish to Blogger as draft first
    clean_title = topic.strip()
    published_url, current_post_id = publisher.publish_post_as_draft(clean_title, cleaned_content, labels=seo_labels)
    
    # 8. Update Google Sheets with draft status
    sheets.update_row_status(row_index, "Draft", url=published_url, post_id=current_post_id, product_count=len(products_data))
    sheets.update_dashboard_stats("Draft")
    sheets.log_execution(topic, "Draft", url=published_url, product_count=len(products_data))
    
    logger.info(f"--- DRAFT PUBLISHED FOR ROW {row_index}: {topic} ---")
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