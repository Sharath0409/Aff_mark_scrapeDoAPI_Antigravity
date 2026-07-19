"""Daily Published-Post Content Reviewer

Reviews already-published Blogger posts for context leakage / topic deviation.
Selects the N oldest unreviewed LIVE posts (topic 1 first), reads the full
content from intro to conclusion, asks the LLM to detect drift, and updates +
republishes the post only when drift is found.

Reuses:
- core.blogger_publisher.BloggerPublisher (list/get/update posts)
- core.content_generator.ContentGenerator (LLM client + _apply_quality_corrections)
- templates.prompts.REVIEW_DRIFT_PROMPT
- core.sheets_manager.SheetsManager (Review Logs tab)
"""

import json
import logging
import re
from typing import List, Dict, Optional

from config import settings
from core.blogger_publisher import BloggerPublisher
from core.content_generator import ContentGenerator
from core.sheets_manager import SheetsManager
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


def run_review(publisher: BloggerPublisher, generator: ContentGenerator, sheets: SheetsManager, count: int = 2, model: str = "deepseek-v4-flash") -> int:
    """Select and review up to `count` posts. Returns number of posts processed."""
    selected = select_posts_for_review(publisher, count=count)
    processed = 0
    for post in selected:
        if review_post(publisher, generator, sheets, post, model=model):
            processed += 1
    logger.info(f"Daily review complete. Processed {processed}/{len(selected)} selected posts.")
    return processed
