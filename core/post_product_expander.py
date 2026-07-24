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


def _find_suitable_parent(tag):
    """Find specific section wrapper parent without selecting the root container."""
    if not tag:
        return None
    parent = tag.parent
    while parent and parent.name in ['div', 'section']:
        classes = parent.get('class', [])
        if isinstance(classes, list) and ('blog-container' in classes or 'article-container' in classes):
            break
        if parent.name == 'section' or (isinstance(classes, list) and any(c in classes for c in ['comparison-table-wrapper', 'faq-section', 'product-section', 'quick-summary-box'])):
            return parent
        parent = parent.parent
    return tag


def repair_article_structure(html_content: str) -> Tuple[str, bool]:
    """Parse HTML and ensure article follows strict sequence:
    Quick Summary -> Product Reviews (P1..Pn) -> Comparison Table -> FAQ -> Conclusion -> Disclaimer -> Related Articles

    If any product review (e.g. Product 4 or Product 5) appears below Comparison Table,
    FAQ, Conclusion/Wrapping Up, Disclaimer, or Related Articles, or if section sequence
    is violated, automatically repair the article by moving DOM elements without regenerating content.

    Returns:
        Tuple[repaired_html_str, was_repaired_bool]
    """
    if not html_content or not html_content.strip():
        return html_content, False

    soup = BeautifulSoup(html_content, 'html.parser')

    # 1. Identify Product Review Sections
    product_sections = soup.find_all('section', class_='product-section')
    if not product_sections:
        product_sections = soup.find_all('div', class_='product-section')
    if not product_sections:
        product_sections = []
        for h3 in soup.find_all('h3', class_='product-title'):
            parent = _find_suitable_parent(h3)
            if parent and parent not in product_sections:
                product_sections.append(parent)

    if not product_sections:
        return html_content, False

    # 2. Identify Boundary Sections
    # A) Comparison Table
    comp_wrapper = soup.find(class_='comparison-table-wrapper')
    if not comp_wrapper:
        comp_table = soup.find('table', class_='comparison-table')
        if comp_table:
            comp_wrapper = _find_suitable_parent(comp_table)
    if not comp_wrapper:
        for tag in soup.find_all(['h2', 'h3']):
            t_text = tag.get_text(strip=True).lower()
            if any(kw in t_text for kw in ['at a glance', 'how they compare', 'comparison table']):
                comp_wrapper = _find_suitable_parent(tag)
                break

    # B) FAQ Section
    faq_section = soup.find(class_='faq-section')
    if not faq_section:
        for tag in soup.find_all(['h2', 'h3']):
            t_text = tag.get_text(strip=True).lower()
            if 'faq' in t_text or 'frequently asked' in t_text:
                faq_section = _find_suitable_parent(tag)
                break

    # C) Wrapping Up / Conclusion Section
    conclusion_section = None
    for tag in soup.find_all(['h2', 'h3']):
        t_text = tag.get_text(strip=True).lower()
        if any(kw in t_text for kw in ['wrapping up', 'conclusion', 'final thought', 'final recommendation']):
            conclusion_section = _find_suitable_parent(tag)
            break
        elif 'bottom line' in t_text:
            if not tag.find_parent(class_='quick-summary-box'):
                conclusion_section = _find_suitable_parent(tag)
                break

    # D) Disclaimer
    disclaimer_section = soup.find('footer')
    if not disclaimer_section:
        for tag in soup.find_all(['div', 'p']):
            if 'disclaimer:' in tag.get_text(strip=True).lower():
                disclaimer_section = _find_suitable_parent(tag)
                break

    # E) Related Articles
    related_section = soup.find(class_='related-articles')
    if not related_section:
        for tag in soup.find_all(['h2', 'h3', 'div']):
            t_text = tag.get_text(strip=True).lower()
            if any(kw in t_text for kw in ['you might also like', 'related articles']):
                related_section = _find_suitable_parent(tag)
                break

    boundary_nodes = [b for b in [comp_wrapper, faq_section, conclusion_section, disclaimer_section, related_section] if b is not None]

    # 3. Check for Sequence Violation / Misplaced Products
    misplaced = False
    all_nodes = list(soup.descendants)

    for p in product_sections:
        for b in boundary_nodes:
            if b in p.parents:
                misplaced = True
                break
            try:
                if all_nodes.index(b) < all_nodes.index(p):
                    misplaced = True
                    break
            except ValueError:
                pass
        if misplaced:
            break

    if not misplaced and len(boundary_nodes) > 1:
        for i in range(len(boundary_nodes) - 1):
            try:
                idx1 = all_nodes.index(boundary_nodes[i])
                idx2 = all_nodes.index(boundary_nodes[i + 1])
                if idx1 > idx2:
                    misplaced = True
                    break
            except ValueError:
                pass

    if not misplaced:
        return html_content, False

    # 4. Perform Structure Repair
    logger.info("Repairing article structure sequence...")

    # Extract all product section nodes in order
    extracted_products = [p.extract() for p in product_sections]

    # Extract all boundary section nodes upfront before reinserting
    ordered_boundary_inputs = [
        ('comp', comp_wrapper),
        ('faq', faq_section),
        ('conclusion', conclusion_section),
        ('disclaimer', disclaimer_section),
        ('related', related_section)
    ]
    extracted_boundaries = []
    for label, b_node in ordered_boundary_inputs:
        if b_node:
            extracted_boundaries.append((label, b_node.extract()))

    qs_anchor = soup.find(class_='quick-summary-box')
    if not qs_anchor:
        for tag in soup.find_all(['h2', 'h3']):
            if any(kw in tag.get_text(strip=True).lower() for kw in ['quick summary', 'the bottom line']):
                qs_anchor = _find_suitable_parent(tag)
                break

    if not qs_anchor:
        qs_anchor = soup.find(['h1', 'h2', 'p'])

    container = soup.find('div', class_='blog-container') or soup

    current_point = qs_anchor
    for p_node in extracted_products:
        if current_point and current_point != container and current_point.parent:
            current_point.insert_after(p_node)
        else:
            container.append(p_node)
        current_point = p_node

    for label, b_node in extracted_boundaries:
        if current_point and current_point != container and current_point.parent:
            current_point.insert_after(b_node)
        else:
            container.append(b_node)
        current_point = b_node

    return str(soup), True


def validate_and_repair_recent_posts(publisher: BloggerPublisher, sheets: SheetsManager, count: int = 4) -> int:
    """Validate and repair the structure of the FOUR most recently updated posts.

    Retrieves Blogger posts, checks structure, and if Product 4 or 5 are below
    Comparison Table, FAQ, Conclusion, Disclaimer, or Related Articles, repairs
    the HTML by moving nodes without regenerating content.

    Returns:
        int: Number of posts repaired.
    """
    logger.info(f"Validating article structure for the {count} most recently updated posts...")
    recent_info = sheets.get_recently_updated_posts(count=count)
    
    blogger_posts = publisher.list_all_posts(max_results=500)
    if not blogger_posts:
        return 0

    posts_to_validate = []

    if recent_info:
        for info in recent_info:
            topic = (info.get("topic") or "").strip().lower()
            url = (info.get("url") or "").strip().lower()
            matched = None
            for p in blogger_posts:
                p_url = (p.get("url") or "").strip().lower()
                p_title = (p.get("title") or "").strip().lower()
                if (url and url in p_url) or (topic and topic in p_title):
                    matched = p
                    break
            if matched and matched not in posts_to_validate:
                posts_to_validate.append(matched)

    if len(posts_to_validate) < count:
        sorted_posts = sorted(blogger_posts, key=lambda x: x.get("updated") or x.get("published") or "", reverse=True)
        for p in sorted_posts:
            if len(posts_to_validate) >= count:
                break
            if p not in posts_to_validate:
                posts_to_validate.append(p)

    repaired_count = 0

    for post in posts_to_validate:
        post_id = post.get("id")
        title = post.get("title", "Untitled")
        if not post_id:
            continue

        full_post = publisher.get_post(post_id)
        content = full_post.get("content", "")
        if not content.strip():
            continue

        repaired_html, was_repaired = repair_article_structure(content)
        if was_repaired:
            logger.info(f"Structure violation detected and repaired for post: '{title}' (ID: {post_id})")
            update_body = {
                "id": post_id,
                "title": full_post.get("title", title),
                "content": repaired_html,
                "labels": full_post.get("labels", []),
            }
            try:
                publisher.update_post(post_id, update_body)
                sheets.log_review(title, "Repaired Structure", "Moved Product 4/5 before Comparison/FAQ/Conclusion", full_post.get("url", ""))
                repaired_count += 1
            except Exception as e:
                logger.error(f"Failed to update repaired post ID {post_id}: {e}")
        else:
            logger.info(f"Article structure already valid for post: '{title}' (ID: {post_id})")

    logger.info(f"Post update validation complete. Repaired {repaired_count}/{len(posts_to_validate)} validated post(s).")
    return repaired_count


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
        
        labels = [l.lower() for l in post.get("labels", []) if isinstance(l, str)]
        if EXPANDED_LABEL.lower() in labels:
            continue

        post_id = post.get("id")
        if not post_id:
            continue

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
    
    context = f"Current Article Context\nArticle Topic: {topic}\nPrimary Keyword: {keyword}\nProducts Reviewed:\n- {product['title']} | {product['price']} | {product['rating']} | URL: {product.get('url', '#')}\n\nPreviously Generated Sections:\n(None yet)\n=========================\n"
    
    full_prompt = context + prompt
    return generator.generate_section(full_prompt, model="deepseek-v4-flash")


def _inject_product_sections(html_content: str, new_products: List[Dict], generator: ContentGenerator, topic: str, keyword: str, insert_after_third: bool = False) -> str:
    """Inject new product sections into the HTML.

    Always places Product 4 immediately after Product 3, and Product 5 immediately after Product 4,
    and runs structure repair to guarantee exact sequence:
    Quick Summary -> Product Reviews -> Comparison Table -> FAQ -> Conclusion -> Disclaimer -> Related Articles
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    product_sections = soup.find_all('section', class_='product-section')
    if not product_sections:
        product_sections = soup.find_all('div', class_='product-section')

    insertion_point = None
    if len(product_sections) >= 3:
        insertion_point = product_sections[2]
    elif len(product_sections) > 0:
        insertion_point = product_sections[-1]
    else:
        qs = soup.find(class_='quick-summary-box')
        if qs:
            insertion_point = qs

    for product in new_products:
        review_html = _generate_review_section(generator, product, topic, keyword)

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

        new_section = BeautifulSoup(section_html, 'html.parser')
        if insertion_point:
            insertion_point.insert_after(new_section)
            insertion_point = new_section
        else:
            soup.append(new_section)
            insertion_point = new_section

    repaired_html, _ = repair_article_structure(str(soup))
    return repaired_html


def expand_post(publisher: BloggerPublisher, generator: ContentGenerator, sheets: SheetsManager, post: Dict, optimizer: ImageOptimizer = None, uploader: BloggerCDNUploader = None, insert_after_third: bool = False) -> bool:
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

    existing_asins = _get_existing_asins(content)
    current_count = _count_product_sections(content)
    needed = 5 - current_count

    if needed <= 0:
        logger.info(f"Post '{title}' already has {current_count} products. Repairing structure if needed...")
        repaired_html, was_repaired = repair_article_structure(content)
        if was_repaired:
            update_body = {
                "id": post_id,
                "title": full_post.get("title", title),
                "content": repaired_html,
                "labels": labels,
            }
            publisher.update_post(post_id, update_body)
            logger.info(f"Repaired structure for already-5-product post ID: {post_id}")
        return True

    logger.info(f"Post has {current_count} products, need {needed} more.")

    new_products = _scrape_new_products(keyword, existing_asins, needed)
    if not new_products:
        logger.warning(f"No new products found for '{title}'. Skipping.")
        return False

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
        if optimizer is None:
            local_optimizer.cleanup()

    updated_html = _inject_product_sections(content, new_products, generator, topic, keyword, insert_after_third=insert_after_third)

    final_html = generator._apply_quality_corrections(updated_html, topic, keyword)
    final_html, _ = repair_article_structure(final_html)

    if EXPANDED_LABEL not in labels:
        labels.append(EXPANDED_LABEL)

    update_body = {
        "id": post_id,
        "title": full_post.get("title", title),
        "content": final_html,
        "labels": labels,
    }
    try:
        publisher.update_post(post_id, update_body)
        logger.info(f"Successfully expanded post ID: {post_id} with {len(new_products)} new products")
        
        sheets.log_review(topic, "Expanded to 5 Products", f"Added {len(new_products)} products", full_post.get("url", ""))
        return True
    except Exception as e:
        logger.error(f"Failed to update post ID {post_id}: {e}")
        return False


def run_expand(publisher: BloggerPublisher, generator: ContentGenerator, sheets: SheetsManager, count: int = 2, optimizer: ImageOptimizer = None, uploader: BloggerCDNUploader = None) -> int:
    """Find and expand up to `count` posts. Returns number of posts processed."""
    selected = find_posts_under_5(publisher, sheets, count=count)
    processed = 0
    local_optimizer = optimizer or ImageOptimizer()
    local_uploader = uploader or BloggerCDNUploader(settings.GCP_SERVICE_ACCOUNT)
    
    try:
        for idx, post in enumerate(selected):
            insert_after_third = idx < 4
            if expand_post(publisher, generator, sheets, post, local_optimizer, local_uploader, insert_after_third):
                processed += 1
    finally:
        if optimizer is None:
            local_optimizer.cleanup()
    
    try:
        validate_and_repair_recent_posts(publisher, sheets, count=4)
    except Exception as e:
        logger.error(f"Failed during post update validation pass: {e}")

    logger.info(f"Daily expand complete. Processed {processed}/{len(selected)} selected posts.")
    return processed