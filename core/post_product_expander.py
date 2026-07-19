"""Post Product Expander

Expands old published posts that have fewer than 5 products to have 5 products.
Reads the original keyword from the Google Sheet, re-scrapes Amazon for missing
products, generates new review sections, and injects them before the FAQ/conclusion.
"""

import json
import logging
import re
from typing import List, Dict, Optional, Tuple

from bs4 import BeautifulSoup

from config import settings
from core.blogger_publisher import BloggerPublisher
from core.content_generator import ContentGenerator
from core.scraper import AmazonScraper
from core.sheets_manager import SheetsManager
from utils.affiliate import inject_affiliate_tag
from utils.image_optimizer import ImageOptimizer
from utils.image_uploader import BloggerCDNUploader

logger = logging.getLogger("post_product_expander")

EXPANDED_LABEL = "Expanded to 5"


def _extract_asin_from_url(url: str) -> Optional[str]:
    """Extract ASIN from Amazon URL."""
    # Amazon URLs typically have /dp/ASIN or /gp/product/ASIN
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'/ASIN/([A-Z0-9]{10})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _get_existing_asins(html_content: str) -> set:
    """Extract ASINs from existing product sections in the HTML."""
    asins: set = set()
    soup = BeautifulSoup(html_content, 'html.parser')
    # Find all buy buttons with Amazon URLs
    for link in soup.find_all('a', href=True):
        href = link['href']
        if 'amazon.com' in href and ('/dp/' in href or '/gp/product/' in href):
            asin = _extract_asin_from_url(href)
            if asin:
                asins.add(asin)
    return asins


def _count_product_sections(html_content: str) -> int:
    """Count the number of product sections in the HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    # Product sections have class="product-section"
    sections = soup.find_all('section', class_='product-section')
    return len(sections)


def find_posts_under_5(publisher: BloggerPublisher, sheets: SheetsManager, count: int = 2) -> List[Dict]:
    """Find LIVE posts with fewer than 5 product sections.

    Returns posts sorted by published date ascending (oldest first).
    """
    logger.info("Fetching published posts to find those with < 5 products...")
    posts = publisher.list_all_posts(max_results=500)
    if not posts:
        logger.info("No posts found in Blogger.")
        return []

    candidates = []
    for post in posts:
        status = (post.get("status") or "LIVE").upper()
        if status != "LIVE":
            continue
        
        # Skip already expanded posts
        labels = [l.lower() for l in post.get("labels", []) if isinstance(l, str)]
        if EXPANDED_LABEL.lower() in labels:
            continue

        post_id = post.get("id")
        if not post_id:
            continue

        # Fetch full content to count product sections
        full_post = publisher.get_post(post_id)
        content = full_post.get("content", "")
        product_count = _count_product_sections(content)
        
        if product_count < 5:
            published_date = post.get("published") or post.get("updated") or ""
            candidates.append((published_date, post, product_count))
            logger.info(f"Found candidate: '{post.get('title', 'Untitled')}' with {product_count} products")

    if not candidates:
        logger.info("No posts found with fewer than 5 products.")
        return []

    # Sort by published date ascending (oldest first)
    candidates.sort(key=lambda item: item[0] or "")
    selected = [item[1] for item in candidates[:count]]
    for s in selected:
        logger.info(f"Selected for expansion: '{s.get('title', 'Untitled')}' (ID: {s.get('id')})")
    return selected


def _get_keyword_from_sheet(sheets: SheetsManager, topic: str) -> Optional[str]:
    """Look up the original keyword for a topic from the Google Sheet."""
    try:
        values = sheets.get_all_rows()
        if not values or len(values) < 2:
            return None
        headers = values[0]
        topic_idx = headers.index("Topic") if "Topic" in headers else 0
        keyword_idx = headers.index("Keyword") if "Keyword" in headers else 1
        
        for row in values[1:]:
            if len(row) > topic_idx and row[topic_idx] == topic:
                return row[keyword_idx] if len(row) > keyword_idx else topic
    except Exception as e:
        logger.error(f"Failed to look up keyword for topic '{topic}': {e}")
    return None


def _scrape_new_products(keyword: str, existing_asins: set, max_new: int) -> List[Dict]:
    """Scrape Amazon for new products not already in the post."""
    scraper = AmazonScraper()
    product_urls = scraper.search_products(keyword)
    if not product_urls:
        logger.warning(f"No products found for keyword: {keyword}")
        return []

    new_products = []
    for url in product_urls:
        if len(new_products) >= max_new:
            break
        asin = _extract_asin_from_url(url)
        if asin and asin in existing_asins:
            logger.info(f"Skipping already-present product ASIN: {asin}")
            continue
        
        data = scraper.scrape_product_details(url)
        if data:
            new_products.append(data)
            if asin:
                existing_asins.add(asin)
    
    return new_products


def _generate_review_section(generator: ContentGenerator, product: Dict, topic: str, keyword: str) -> str:
    """Generate a review section for a single product."""
    from templates.prompts import REVIEW_TEMPLATE
    
    prompt = REVIEW_TEMPLATE.format(
        title=product['title'],
        price=product['price'],
        rating=product['rating'],
        review_count=product['review_count'],
        features=product['features']
    )
    
    # Build context similar to generate_full_post
    context = f"Current Article Context\nArticle Topic: {topic}\nPrimary Keyword: {keyword}\nProducts Reviewed:\n- {product['title']} | {product['price']} | {product['rating']} | URL: {product.get('url', '#')}\n\nPreviously Generated Sections:\n(None yet)\n=========================\n"
    
    full_prompt = context + prompt
    return generator.generate_section(full_prompt, model="deepseek-v4-flash")


def _inject_product_sections(html_content: str, new_products: List[Dict], generator: ContentGenerator, topic: str, keyword: str) -> str:
    """Inject new product sections before FAQ/conclusion/footer."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find insertion point: before FAQ, conclusion, or footer
    insertion_point = None
    for tag in soup.find_all(['h2', 'h3']):
        text = tag.get_text(strip=True).lower()
        if any(kw in text for kw in ['faq', 'frequently asked', 'conclusion', 'final thought', 'final recommendation', 'bottom line']):
            insertion_point = tag
            break
    
    if not insertion_point:
        # Fallback: before footer
        footer = soup.find('footer')
        if footer:
            insertion_point = footer
        else:
            # Last resort: append to body
            body = soup.find('div', class_='blog-container') or soup
            insertion_point = body
    
    # Generate and inject each new product section
    for product in new_products:
        review_html = _generate_review_section(generator, product, topic, keyword)
        
        # Build product section HTML
        image_html = ""
        if product.get('image_url'):
            width_attr = f' width="{product.get("image_width")}"' if product.get("image_width") else ''
            height_attr = f' height="{product.get("image_height")}"' if product.get("image_height") else ''
            image_html = f'<div class="product-image-centered"><img src="{product["image_url"]}" alt="{product["title"]}"{width_attr}{height_attr} loading="lazy"></div>'
        
        section_html = f"""
        <section class="product-section">
            <h3 class="product-title">{product['title']}</h3>
            {image_html}
            <div class="product-summary-full">
                <div class="price-badge">Price: {product['price']}</div>
                {review_html}
            </div>
            <div class="buy-button-wrapper">
                <a href="{product['url']}" target="_blank" rel="nofollow sponsored" class="buy-btn">View Latest Price on Amazon</a>
            </div>
        </section>
        """
        
        # Parse and insert
        new_section = BeautifulSoup(section_html, 'html.parser')
        if insertion_point:
            insertion_point.insert_before(new_section)
        else:
            soup.append(new_section)
    
    return str(soup)


def expand_post(publisher: BloggerPublisher, generator: ContentGenerator, sheets: SheetsManager, post: Dict, optimizer: ImageOptimizer = None, uploader: BloggerCDNUploader = None) -> bool:
    """Expand a single post to have 5 products.
    
    Args:
        publisher: Blogger publisher instance
        generator: Content generator instance
        sheets: Sheets manager instance
        post: Post dictionary with id, title, labels
        optimizer: Optional ImageOptimizer instance (creates new if not provided)
        uploader: Optional BloggerCDNUploader instance (creates new if not provided)
    """
    post_id = post.get("id")
    title = post.get("title", "Untitled")
    if not post_id:
        logger.error("Post missing an ID; skip.")
        return False

    logger.info(f"Fetching full content for post ID: {post_id}")
    full_post = publisher.get_post(post_id)
    content = full_post.get("content", "")
    if not content.strip():
        logger.warning(f"Post '{title}' has no content. Skipping.")
        return False

    # Get topic and keyword
    topic = title
    labels = full_post.get("labels", []) or []
    if isinstance(labels, str):
        labels = [labels]
    for label in labels:
        if isinstance(label, str) and label.lower() not in ["quality reviewed", "expanded to 5"] and len(label) > 3:
            topic = label
            break

    keyword = _get_keyword_from_sheet(sheets, topic)
    if not keyword:
        keyword = topic
        logger.warning(f"Could not find keyword in sheet for '{topic}', using topic as keyword")

    logger.info(f"Expanding post '{title}' (topic: {topic}, keyword: {keyword})")

    # Get existing ASINs
    existing_asins = _get_existing_asins(content)
    current_count = _count_product_sections(content)
    needed = 5 - current_count

    if needed <= 0:
        logger.info(f"Post '{title}' already has {current_count} products. Skipping.")
        return True

    logger.info(f"Post has {current_count} products, need {needed} more.")

    # Scrape new products
    new_products = _scrape_new_products(keyword, existing_asins, needed)
    if not new_products:
        logger.warning(f"No new products found for '{title}'. Skipping.")
        return False

    # Process images for new products - use provided instances or create new ones
    local_optimizer = optimizer or ImageOptimizer()
    local_uploader = uploader or BloggerCDNUploader(settings.GCP_SERVICE_ACCOUNT)
    
    try:
        for product in new_products:
            raw_image_url = product.get('image_url')
            if raw_image_url:
                logger.info(f"Processing image for: {product.get('title')}")
                temp_webp, img_w, img_h = local_optimizer.process_from_url(raw_image_url, product.get('title', 'product'))
                if temp_webp:
                    cdn_url = local_uploader.upload_to_google_cdn(temp_webp, bucket_name=settings.GCS_BUCKET_NAME)
                    if cdn_url:
                        product['image_url'] = cdn_url
                        product['image_width'] = img_w
                        product['image_height'] = img_h
    finally:
        # Only cleanup if we created our own optimizer
        if optimizer is None:
            local_optimizer.cleanup()

    # Inject new product sections
    updated_html = _inject_product_sections(content, new_products, generator, topic, keyword)

    # Apply quality corrections
    final_html = generator._apply_quality_corrections(updated_html, topic, keyword)

    # Add Expanded to 5 label
    if EXPANDED_LABEL not in labels:
        labels.append(EXPANDED_LABEL)

    # Update post on Blogger
    update_body = {
        "id": post_id,
        "title": full_post.get("title", title),
        "content": final_html,
        "labels": labels,
    }
    try:
        publisher.update_post(post_id, update_body)
        logger.info(f"Successfully expanded post ID: {post_id} with {len(new_products)} new products")
        
        # Log to sheets
        sheets.log_review(topic, "Expanded to 5 Products", f"Added {len(new_products)} products", full_post.get("url", ""))
        return True
    except Exception as e:
        logger.error(f"Failed to update post ID {post_id}: {e}")
        return False


def run_expand(publisher: BloggerPublisher, generator: ContentGenerator, sheets: SheetsManager, count: int = 2, optimizer: ImageOptimizer = None, uploader: BloggerCDNUploader = None) -> int:
    """Find and expand up to `count` posts. Returns number of posts processed."""
    selected = find_posts_under_5(publisher, sheets, count=count)
    processed = 0
    # Create shared optimizer/uploader if not provided
    local_optimizer = optimizer or ImageOptimizer()
    local_uploader = uploader or BloggerCDNUploader(settings.GCP_SERVICE_ACCOUNT)
    
    try:
        for post in selected:
            if expand_post(publisher, generator, sheets, post, local_optimizer, local_uploader):
                processed += 1
    finally:
        if optimizer is None:
            local_optimizer.cleanup()
    
    logger.info(f"Daily expand complete. Processed {processed}/{len(selected)} selected posts.")
    return processed