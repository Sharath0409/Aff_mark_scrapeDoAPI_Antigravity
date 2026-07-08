#!/usr/bin/env python3
"""Daily Published Article Review and Correction

This script fetches one published Blogger post that has not yet been marked as quality-reviewed,
checks it for template leaks, robotic phrasing, and topic drift, and updates the content if needed.
It also tags the post with a review label so the same article does not get reviewed repeatedly.
"""

import os
import sys
import logging
import argparse
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from core.blogger_publisher import BloggerPublisher
from core.content_generator import ContentGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("daily_published_review")

QUALITY_LABEL = "Quality Reviewed"
REVIEWED_LABELS = {QUALITY_LABEL.lower(), "quality-reviewed", "quality_reviewed"}


def select_next_post(publisher):
    """Select the next published post that does not have the quality-review label."""
    logger.info("Fetching published posts for review...")
    posts = publisher.list_all_posts(max_results=500)
    if not posts:
        logger.info("No posts found in Blogger.")
        return None

    unreviewed = []
    for post in posts:
        status = post.get("status", "LIVE").upper()
        if status != "LIVE":
            continue

        labels = [label.lower() for label in post.get("labels", []) if isinstance(label, str)]
        if any(label in REVIEWED_LABELS for label in labels):
            continue

        published_date = post.get("published") or post.get("updated") or ""
        unreviewed.append((published_date, post))

    if not unreviewed:
        logger.info("All published posts appear to be quality-reviewed.")
        return None

    unreviewed.sort(key=lambda item: item[0] or "")
    selected = unreviewed[0][1]
    logger.info(f"Selected post for review: '{selected.get('title', 'Untitled')}' (ID: {selected.get('id')})")
    return selected


def apply_review(publisher, generator, post):
    """Review and correct the post content if necessary."""
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

    logger.info("Applying quality corrections to existing content...")
    labels = full_post.get("labels") or []
    topic = title
    for label in labels:
        if label.lower() not in REVIEWED_LABELS and len(label) > 3:
            topic = label
            break

    corrected_content = generator._apply_quality_corrections(content, title, topic)
    labels = full_post.get("labels") or []
    if isinstance(labels, str):
        labels = [labels]

    if QUALITY_LABEL not in labels:
        labels.append(QUALITY_LABEL)

    if corrected_content.strip() == content.strip() and labels == full_post.get("labels", []):
        logger.info("No content changes needed. Marking as reviewed.")
        full_post["labels"] = labels
        publisher.update_post(post_id, {"labels": labels})
        return True

    logger.info("Updating post content and review label.")
    full_post["content"] = corrected_content
    full_post["labels"] = labels
    try:
        publisher.update_post(post_id, full_post)
        logger.info(f"Successfully updated post ID: {post_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update post ID {post_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Review one published Blogger post daily and correct content if needed.")
    parser.add_argument("--apply", action="store_true", help="Apply updates live to Blogger.")
    args = parser.parse_args()

    if not args.apply:
        logger.info("Dry run mode: no updates will be saved. Use --apply to make live changes.")

    try:
        publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        generator = ContentGenerator()
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)

    selected = select_next_post(publisher)
    if not selected:
        return

    if args.apply:
        updated = apply_review(publisher, generator, selected)
        if updated:
            logger.info("Daily published article review completed.")
        else:
            logger.info("Daily published article review completed with no updates applied.")
    else:
        logger.info("Dry run complete. No updates were made.")


if __name__ == "__main__":
    main()
