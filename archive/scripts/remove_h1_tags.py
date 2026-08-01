#!/usr/bin/env python3
"""
Remove H1 Tags from Blogger Posts
Processes all published Blogger posts:
  1. Compares H1 tag content with the post title. If it matches, deletes the H1.
  2. Converts any other H1 tags to H2 tags.
  3. Updates the post content without modifying the post title.
"""

import os
import sys
import logging
import argparse
import time
import requests
from bs4 import BeautifulSoup

# Project path setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from core.blogger_publisher import BloggerPublisher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("h1_remover")

class BloggerH1Remover:
    def __init__(self, dry_run=True):
        self.publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        self.dry_run = dry_run
        self.stats = {
            "posts_scanned": 0,
            "posts_updated": 0,
            "h1_deleted": 0,
            "h1_converted_to_h2": 0
        }

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
                self.stats["h1_deleted"] += 1
                logger.info(f"  ✂ Deleted H1 matching title: '{h1_text}'")
                did_change = True
            else:
                # Rename the H1 tag to H2
                h1.name = "h2"
                self.stats["h1_converted_to_h2"] += 1
                logger.info(f"  🔄 Converted H1 to H2: '{h1_text}'")
                did_change = True

        return str(soup), did_change

    def run(self):
        mode = "DRY RUN (no changes applied)" if self.dry_run else "LIVE (changes will be saved)"
        logger.info(f"Starting H1 tag processing pipeline in {mode}...")

        # Fetch posts
        posts = []
        page_token = None
        while True:
            resp = (
                self.publisher.service.posts()
                .list(
                    blogId=self.publisher.blog_id,
                    pageToken=page_token,
                    maxResults=500,
                    fetchBodies=True
                )
                .execute()
            )
            items = resp.get("items", [])
            if not items:
                break
            posts.extend(items)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        logger.info(f"Retrieved {len(posts)} posts from Blogger.")

        for i, post in enumerate(posts, 1):
            post_id = post["id"]
            title = post.get("title", "Untitled")
            content = post.get("content", "")

            logger.info(f"[{i}/{len(posts)}] Processing post: '{title}' (ID: {post_id})")
            self.stats["posts_scanned"] += 1

            new_content, changed = self.clean_post_h1(title, content)

            if changed:
                self.stats["posts_updated"] += 1
                if not self.dry_run:
                    try:
                        post["content"] = new_content
                        self.publisher.update_post(post_id, post)
                        logger.info("  ✅ Updated live post on Blogger.")
                        time.sleep(1.5)  # API rate limit buffer
                    except Exception as e:
                        logger.error(f"  ❌ Failed to update post: {e}")
            else:
                logger.info("  — No H1 tags found.")

        # Summary
        logger.info("=" * 60)
        logger.info(f"H1 Processing Summary ({'DRY RUN' if self.dry_run else 'APPLIED'}):")
        logger.info(f"  Posts scanned: {self.stats['posts_scanned']}")
        logger.info(f"  Posts with H1 changes: {self.stats['posts_updated']}")
        logger.info(f"  H1 tags deleted: {self.stats['h1_deleted']}")
        logger.info(f"  H1 tags converted to H2: {self.stats['h1_converted_to_h2']}")
        logger.info("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Remove/Convert H1 tags on Blogger posts.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply updates live to Blogger (default is dry-run)."
    )
    args = parser.parse_args()

    remover = BloggerH1Remover(dry_run=not args.apply)
    remover.run()

if __name__ == "__main__":
    main()
