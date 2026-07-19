#!/usr/env python3
"""Daily Published Article Review and Correction

Reviews already-published Blogger posts for context leakage / topic deviation.
By default it processes the 2 oldest unreviewed LIVE posts per day (starting
from topic 1), reading each from intro to conclusion. If drift is detected the
content is corrected and republished; otherwise the post is simply tagged
"Quality Reviewed" so it is not reviewed again.

Usage:
    python scripts/daily_published_review.py          # dry run (no live updates)
    python scripts/daily_published_review.py --apply   # apply updates to Blogger
    python scripts/daily_published_review.py --count 3 # override posts-per-run
"""

import os
import sys
import logging
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from core.blogger_publisher import BloggerPublisher
from core.content_generator import ContentGenerator
from core.content_reviewer import run_review
from core.sheets_manager import SheetsManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("daily_published_review")


def main():
    parser = argparse.ArgumentParser(
        description="Review published Blogger posts daily and correct content drift if needed."
    )
    parser.add_argument("--apply", action="store_true", help="Apply updates live to Blogger.")
    parser.add_argument("--count", type=int, default=2, help="Number of posts to review this run.")
    args = parser.parse_args()

    if not args.apply:
        logger.info("Dry run mode: no updates will be saved. Use --apply to make live changes.")

    try:
        publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        generator = ContentGenerator()
        sheets = SheetsManager(settings.GOOGLE_SHEET_ID, settings.GCP_SERVICE_ACCOUNT)
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)

    if args.apply:
        processed = run_review(publisher, generator, sheets, count=args.count)
        logger.info(f"Daily published article review completed. Processed {processed} post(s).")
    else:
        # Dry run: just report which posts would be selected.
        from core.content_reviewer import select_posts_for_review
        selected = select_posts_for_review(publisher, count=args.count)
        if not selected:
            logger.info("Dry run complete. No unreviewed posts found.")
        else:
            for s in selected:
                logger.info(f"Would review: '{s.get('title', 'Untitled')}' (ID: {s.get('id')})")
            logger.info(f"Dry run complete. {len(selected)} post(s) would be reviewed.")


if __name__ == "__main__":
    main()
