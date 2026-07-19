#!/usr/bin/env python3
"""Daily Old Post Expander

Expands already-published Blogger posts that have fewer than 5 products
to have 5 products. By default it processes the 2 oldest such posts per day.

For each post:
1. Reads the original keyword from the Google Sheet
2. Re-scrapes Amazon for up to 5 products using that keyword
3. Excludes products already present in the post
4. Generates new review sections for the missing products
5. Injects the new sections before the FAQ/conclusion
6. Updates the post on Blogger and tags it "Expanded to 5"

Usage:
    python scripts/expand_old_posts.py          # dry run (no live updates)
    python scripts/expand_old_posts.py --apply   # apply updates to Blogger
    python scripts/expand_old_posts.py --count 3 # override posts-per-run
"""

import os
import sys
import logging
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from core.blogger_publisher import BloggerPublisher
from core.content_generator import ContentGenerator
from core.scraper import AmazonScraper
from core.sheets_manager import SheetsManager
from core.post_product_expander import find_posts_under_5, expand_post

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("expand_old_posts")


def main():
    parser = argparse.ArgumentParser(
        description="Expand old published Blogger posts from 3 to 5 products."
    )
    parser.add_argument("--apply", action="store_true", help="Apply updates live to Blogger.")
    parser.add_argument("--count", type=int, default=2, help="Number of posts to expand this run.")
    args = parser.parse_args()

    if not args.apply:
        logger.info("Dry run mode: no updates will be saved. Use --apply to make live changes.")

    try:
        publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        generator = ContentGenerator()
        scraper = AmazonScraper()
        sheets = SheetsManager(settings.GOOGLE_SHEET_ID, settings.GCP_SERVICE_ACCOUNT)
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)

    if args.apply:
        processed = 0
        selected = find_posts_under_5(publisher, sheets, count=args.count)
        for post in selected:
            if expand_post(publisher, generator, scraper, sheets, post):
                processed += 1
        logger.info(f"Daily expand complete. Processed {processed}/{len(selected)} selected posts.")
    else:
        # Dry run: just report which posts would be selected
        selected = find_posts_under_5(publisher, sheets, count=args.count)
        if not selected:
            logger.info("Dry run complete. No posts found with fewer than 5 products.")
        else:
            for s in selected:
                logger.info(f"Would expand: '{s.get('title', 'Untitled')}' (ID: {s.get('id')})")
            logger.info(f"Dry run complete. {len(selected)} post(s) would be expanded.")


if __name__ == "__main__":
    main()