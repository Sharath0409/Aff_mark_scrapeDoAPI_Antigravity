"""Daily Published-Post Content Reviewer and Regenerator

Reviews already-published Blogger posts for context leakage / topic deviation.
Selects the N oldest unreviewed LIVE posts (topic 1 first), reads the full
content from intro to conclusion, asks the LLM to detect drift, and updates +
republishes the post only when drift is found.

ALSO PROVIDES: Full article regeneration using current production pipeline.
Reuses existing production components to upgrade older articles to current standards.

Reuses:
- core.blogger_publisher.BloggerPublisher (list/get/update posts)
- core.content_generator.ContentGenerator (LLM client + _apply_quality_corrections)
- templates.prompts.REVIEW_DRIFT_PROMPT
- core.sheets_manager.SheetsManager (Review Logs tab)
- core.scraper.AmazonScraper (product scraping)
- core.internal_linker.InternalLinkManager (internal linking)
- utils.image_optimizer.ImageOptimizer (image optimization)
- utils.image_uploader.BloggerCDNUploader (image upload)
"""

import json
import logging
import re
import time
from typing import List, Dict, Optional

from config import settings
from core.blogger_publisher import BloggerPublisher
from core.content_generator import ContentGenerator
from core.scraper import AmazonScraper
from core.internal_linker import InternalLinkManager
from core.sheets_manager import SheetsManager
from utils.image_optimizer import ImageOptimizer
from utils.image_uploader import BloggerCDNUploader
from templates.prompts import REVIEW_DRIFT_PROMPT

logger = logging.getLogger("content_reviewer")

QUALITY_LABEL = "Quality Reviewed"
REVIEWED_LABELS = {QUALITY_LABEL.lower(), "quality-reviewed", "quality_reviewed"}


def _extract_topic(post: Dict, fallback_title: str) -> str:
    """Derive the article topic from title + labels (reused from daily_published_review)."""
    title = post.get("title", fallback_title) or fallback_title
    labels = post.get("labels", []) or []
    if isinstance(labels, str):
        labels = [labels]
    topic = title
    for label in labels:
        if isinstance(label, str) and label.lower() not in REVIEWED_LABELS and len(label) > 3:
            topic = label
            break
    return topic


def select_posts_for_review(publisher: BloggerPublisher, count: int = 2) -> List[Dict]:
    """Select the `count` oldest LIVE posts that have not been quality-reviewed yet.

    Posts are sorted by published date ascending so we always start from topic 1.
    """
    logger.info("Fetching published posts for review...")
    posts = publisher.list_all_posts(max_results=500)
    if not posts:
        logger.info("No posts found in Blogger.")
        return []

    unreviewed = []
    for post in posts:
        status = (post.get("status") or "LIVE").upper()
        if status != "LIVE":
            continue
        labels = [l.lower() for l in post.get("labels", []) if isinstance(l, str)]
        if any(label in REVIEWED_LABELS for label in labels):
            continue
        published_date = post.get("published") or post.get("updated") or ""
        unreviewed.append((published_date, post))

    if not unreviewed:
        logger.info("All published posts appear to be quality-reviewed.")
        return []

    unreviewed.sort(key=lambda item: item[0] or "")
    selected = [item[1] for item in unreviewed[:count]]
    for s in selected:
        logger.info(f"Selected for review: '{s.get('title', 'Untitled')}' (ID: {s.get('id')})")
    return selected


def _strip_code_fences(text: str) -> str:
    """Remove accidental ```json / ``` wrappers the model may add."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(cleaned.split("\n")[1:])
    if cleaned.endswith("```"):
        cleaned = "\n".join(cleaned.split("\n")[:-1])
    cleaned = cleaned.strip()
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    return cleaned


def review_post(publisher: BloggerPublisher, generator: ContentGenerator, sheets: SheetsManager, post: Dict, model: str = "deepseek-v4-flash") -> bool:
    """Review a single post for drift and update it on Blogger if needed.

    Returns True if the post was processed (updated or marked reviewed), False on error.
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

    topic = _extract_topic(full_post, title)
    keyword = topic  # Best-effort keyword fallback; topic is the anchor for drift checks.

    logger.info(f"Running LLM drift check on '{title}' (topic: {topic})...")
    prompt = REVIEW_DRIFT_PROMPT.format(topic=topic, keyword=keyword, html_content=content)
    try:
        response = generator.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        analysis = json.loads(_strip_code_fences(raw))
    except Exception as e:
        logger.error(f"Drift-check LLM call failed for '{title}': {e}")
        return False

    drift_detected = bool(analysis.get("drift_detected", False))
    drift_summary = analysis.get("drift_summary", "") or ""
    corrected_html = (analysis.get("corrected_html") or "").strip()

    labels = full_post.get("labels") or []
    if isinstance(labels, str):
        labels = [labels]
    if QUALITY_LABEL not in labels:
        labels.append(QUALITY_LABEL)

    if not drift_detected or not corrected_html:
        logger.info(f"No drift detected for '{title}'. Marking as reviewed.")
        try:
            publisher.update_post(post_id, {"labels": labels})
        except Exception as e:
            logger.error(f"Failed to tag '{title}' as reviewed: {e}")
            return False
        # Log the review (no drift)
        sheets.log_review(topic, "Reviewed - No Drift", drift_summary)
        return True

    logger.info(f"Drift detected for '{title}': {drift_summary}")

    # Safety net: run the existing regex-based quality corrections on the corrected HTML.
    final_html = generator._apply_quality_corrections(corrected_html, topic, keyword)

    if final_html.strip() == content.strip() and labels == full_post.get("labels", []):
        logger.info(f"Corrected content identical to original for '{title}'. Marking reviewed only.")
        try:
            publisher.update_post(post_id, {"labels": labels})
        except Exception as e:
            logger.error(f"Failed to tag '{title}' as reviewed: {e}")
            return False
        sheets.log_review(topic, "Reviewed - No Changes Needed", drift_summary)
        return True

    logger.info(f"Updating post '{title}' with drift-corrected content.")
    update_body = {
        "id": post_id,
        "title": full_post.get("title", title),
        "content": final_html,
        "labels": labels,
    }
    try:
        publisher.update_post(post_id, update_body)
        logger.info(f"Successfully updated post ID: {post_id}")
        sheets.log_review(topic, "Drift Corrected", drift_summary)
        return True
    except Exception as e:
        logger.error(f"Failed to update post ID {post_id}: {e}")
        return False


def regenerate_post(
    publisher: BloggerPublisher,
    generator: ContentGenerator,
    sheets: SheetsManager,
    scraper: AmazonScraper,
    post: Dict,
    link_manager: InternalLinkManager,
    optimizer: ImageOptimizer,
    uploader: BloggerCDNUploader,
    row: Dict,
) -> bool:
    """Fully regenerate an existing post using the current production pipeline.
    
    This upgrades older articles to match the latest production standards:
    - Five-product reviews with latest scraped products
    - Enhanced introduction and Quick Summary
    - Latest comparison table format
    - Latest FAQ section
    - Latest Wrapping Up / Conclusion
    - EEAT improvements and OSHA guidance where applicable
    - AI image planning, generation, optimization, upload, and injection
    - Internal linking with current InternalLinkManager
    - Current production HTML layout
    
    Preserves: Blogger Post ID, URL/permalink, analytics history, comments, publish date.
    
    Args:
        publisher: BloggerPublisher instance
        generator: ContentGenerator instance
        sheets: SheetsManager instance
        scraper: AmazonScraper instance
        post: Post dict from Blogger API (with id, title, labels)
        link_manager: InternalLinkManager instance
        optimizer: ImageOptimizer instance
        uploader: BloggerCDNUploader instance
        row: Row dict from Google Sheets (Topic, Keyword, Category, row_index)
        
    Returns:
        True if successful, False on error
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

    topic = _extract_topic(full_post, title)
    
    # Get keyword from Google Sheets row if available, otherwise use topic
    keyword = row.get("Keyword", "") if row else topic
    if not keyword:
        keyword = topic
    
    category = row.get("Category", "") if row else ""
    row_index = row.get("row_index") if row else None

    logger.info(f"Regenerating post '{title}' (topic: {topic}, keyword: {keyword}) using production pipeline...")

    try:
        # 1. Refresh post corpus for internal linking
        link_manager.refresh_corpus()
        
        # 2. Scrape latest products (up to 5)
        logger.info(f"Scraping Amazon for keyword: {keyword}")
        product_urls = scraper.search_products(keyword)
        if not product_urls:
            logger.error(f"No products found for keyword '{keyword}'.")
            return False
        
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
            logger.error(f"Scraped details failed for all search results for: {keyword}")
            return False
        
        # 3. Generate full post using current production pipeline
        logger.info("Generating full post content with production pipeline...")
        html_content = generator.generate_full_post(topic, keyword, products_data)
        
        # 4. Generate SEO labels
        seo_labels = generator.generate_seo_tags(topic, keyword)
        if category and category not in seo_labels:
            seo_labels.append(category)
        
        # 5. Internal linking
        related_posts = link_manager.get_related_articles(topic, seo_labels, count=3)
        if related_posts:
            html_content = link_manager.inject_internal_links(html_content, related_posts)
            html_content = link_manager.add_related_section(html_content, related_posts)
        
        # 6. Clean H1 tags before publishing
        from scripts.remove_h1_tags import BloggerH1Remover
        h1_remover = BloggerH1Remover(dry_run=False)
        cleaned_content, _ = h1_remover.clean_post_h1(topic.strip(), html_content)
        
        # 7. Update the existing Blogger post (preserves ID, URL, analytics, comments)
        logger.info(f"Updating existing Blogger post ID: {post_id}")
        update_body = {
            "id": post_id,
            "title": full_post.get("title", title),
            "content": cleaned_content,
            "labels": seo_labels,
        }
        publisher.update_post(post_id, update_body)
        logger.info(f"Successfully regenerated and updated post ID: {post_id}")
        
        # 8. Update Google Sheets if row_index available
        if row_index:
            published_url = full_post.get("url", "")
            sheets.update_row_status(row_index, "Success", url=published_url, post_id=post_id, product_count=len(products_data))
            sheets.update_dashboard_stats("Success")
            sheets.log_execution(topic, "Regenerated", url=published_url, product_count=len(products_data))
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to regenerate post ID {post_id}: {e}", exc_info=True)
        # Update sheets with failure if row_index available
        if row and row.get("row_index"):
            try:
                sheets.update_row_status(row["row_index"], "Failed", error=str(e))
                sheets.update_dashboard_stats("Failed")
                sheets.log_execution(topic, "Regeneration Failed", error=str(e))
            except Exception:
                pass
        return False


def select_posts_for_regeneration(publisher: BloggerPublisher, count: int = 2) -> List[Dict]:
    """Select the `count` oldest LIVE posts that have not been regenerated yet.

    Posts are sorted by published date ascending so we always start from topic 1.
    """
    logger.info("Fetching published posts for regeneration...")
    posts = publisher.list_all_posts(max_results=500)
    if not posts:
        logger.info("No posts found in Blogger.")
        return []

    unregenerated = []
    REGENERATED_LABELS = {"regenerated", "updated to 5", "expanded to 5", "quality reviewed"}
    for post in posts:
        status = (post.get("status") or "LIVE").upper()
        if status != "LIVE":
            continue
        labels = [l.lower() for l in post.get("labels", []) if isinstance(l, str)]
        if any(label in REGENERATED_LABELS for label in labels):
            continue
        published_date = post.get("published") or post.get("updated") or ""
        unregenerated.append((published_date, post))

    if not unregenerated:
        logger.info("All published posts appear to be regenerated or reviewed.")
        return []

    unregenerated.sort(key=lambda item: item[0] or "")
    selected = [item[1] for item in unregenerated[:count]]
    for s in selected:
        logger.info(f"Selected for regeneration: '{s.get('title', 'Untitled')}' (ID: {s.get('id')})")
    return selected


def _find_sheet_row_for_topic(sheets: SheetsManager, topic: str) -> Optional[Dict]:
    """Find the Google Sheets row for a given topic."""
    try:
        values = sheets.get_all_rows()
        if not values or len(values) < 2:
            return None
        headers = values[0]
        topic_idx = headers.index("Topic") if "Topic" in headers else 0
        keyword_idx = headers.index("Keyword") if "Keyword" in headers else 1
        category_idx = headers.index("Category") if "Category" in headers else 2
        
        for idx, row in enumerate(values[1:], start=2):
            if len(row) > topic_idx and row[topic_idx] == topic:
                return {
                    "row_index": idx,
                    "Topic": row[topic_idx] if len(row) > topic_idx else "",
                    "Keyword": row[keyword_idx] if len(row) > keyword_idx else "",
                    "Category": row[category_idx] if len(row) > category_idx else "",
                }
    except Exception as e:
        logger.warning(f"Could not find sheet row for topic '{topic}': {e}")
    return None


def run_regeneration(
    publisher: BloggerPublisher,
    generator: ContentGenerator,
    sheets: SheetsManager,
    scraper: AmazonScraper,
    link_manager: InternalLinkManager,
    optimizer: ImageOptimizer,
    uploader: BloggerCDNUploader,
    count: int = 2,
) -> int:
    """Select and regenerate up to `count` posts. Returns number of posts processed."""
    selected = select_posts_for_regeneration(publisher, count=count)
    processed = 0
    for post in selected:
        topic = _extract_topic(post, post.get("title", "Untitled"))
        row = _find_sheet_row_for_topic(sheets, topic)
        if regenerate_post(
            publisher, generator, sheets, scraper, post,
            link_manager, optimizer, uploader, row
        ):
            processed += 1
    logger.info(f"Daily regeneration complete. Processed {processed}/{len(selected)} selected posts.")
    return processed


def run_review(publisher: BloggerPublisher, generator: ContentGenerator, sheets: SheetsManager, count: int = 2, model: str = "deepseek-v4-flash") -> int:
    """Select and review up to `count` posts. Returns number of posts processed."""
    selected = select_posts_for_review(publisher, count=count)
    processed = 0
    for post in selected:
        if review_post(publisher, generator, sheets, post, model=model):
            processed += 1
    logger.info(f"Daily review complete. Processed {processed}/{len(selected)} selected posts.")
    return processed
