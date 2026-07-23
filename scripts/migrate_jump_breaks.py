#!/usr/bin/env python3
"""Blogger Jump Break Migration Script

One-time migration to add <!--more--> jump breaks to all existing published posts.

Usage:
    python scripts/migrate_jump_breaks.py --dry-run    # Preview changes
    python scripts/migrate_jump_breaks.py --apply      # Apply changes
"""

import sys
import os
import argparse
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.logger import get_logger
from config import settings
from core.blogger_publisher import BloggerPublisher, insert_jump_break

logger = get_logger("migrate_jump_breaks")


def process_posts(publisher: BloggerPublisher, dry_run: bool = True):
    """Process all published posts and add jump breaks where missing.
    
    Args:
        publisher: BloggerPublisher instance
        dry_run: If True, only preview changes without updating
        
    Returns:
        dict with counts: processed, updated, skipped, failed
    """
    stats = {
        'processed': 0,
        'updated': 0,
        'skipped': 0,
        'failed': 0,
        'already_has_jump_break': 0
    }
    
    start_time = time.time()
    
    logger.info("Fetching all published posts...")
    posts = publisher.list_all_posts(max_results=1000)
    
    if not posts:
        logger.warning("No posts found")
        return stats
    
    logger.info(f"Found {len(posts)} posts to process")
    
    for post in posts:
        post_id = post.get('id')
        title = post.get('title', 'Untitled')
        status = post.get('status', 'UNKNOWN')
        
        # Only process LIVE (published) posts
        if status != 'LIVE':
            stats['skipped'] += 1
            logger.debug(f"Skipping post {post_id} ({title}) - status: {status}")
            continue
        
        stats['processed'] += 1
        
        try:
            # Fetch full post content
            full_post = publisher.get_post(post_id)
            content = full_post.get('content', '')
            
            # Check if jump break already exists
            if '<!--more-->' in content:
                stats['already_has_jump_break'] += 1
                logger.info(f"SKIPPED: Post {post_id} - {title} (already has jump break)")
                continue
            
            # Apply jump break insertion
            new_content = insert_jump_break(content)
            
            # Verify change was made
            if new_content == content:
                logger.warning(f"No change for post {post_id} - {title}")
                stats['skipped'] += 1
                continue
            
            if dry_run:
                logger.info(f"DRY-RUN: Would UPDATE post {post_id} - {title}")
                stats['updated'] += 1
            else:
                # Update the post
                update_body = {
                    "id": post_id,
                    "title": title,
                    "content": new_content,
                    "labels": full_post.get('labels', [])
                }
                publisher.update_post(post_id, update_body)
                logger.info(f"UPDATED: Post {post_id} - {title}")
                stats['updated'] += 1
                
        except Exception as e:
            logger.error(f"FAILED: Post {post_id} - {title}: {e}")
            stats['failed'] += 1
            # Continue processing other posts
    
    elapsed = time.time() - start_time
    
    # Print summary report
    print("\n" + "=" * 50)
    print("MIGRATION REPORT")
    print("=" * 50)
    print(f"Mode              : {'DRY-RUN' if dry_run else 'APPLY'}")
    print(f"Total Fetched     : {len(posts)}")
    print(f"Processed (LIVE)  : {stats['processed']}")
    print(f"Updated           : {stats['updated']}")
    print(f"Skipped (non-LIVE): {stats['skipped']}")
    print(f"Already Has JB    : {stats['already_has_jump_break']}")
    print(f"Failed            : {stats['failed']}")
    print(f"Execution Time    : {elapsed:.2f} seconds")
    print("=" * 50)
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Migrate existing Blogger posts to add jump breaks"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Preview changes without updating (default)'
    )
    parser.add_argument(
        '--apply',
        action='store_false',
        dest='dry_run',
        help='Actually update posts on Blogger'
    )
    args = parser.parse_args()
    
    logger.info(f"Starting jump break migration (dry_run={args.dry_run})")
    
    try:
        publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        process_posts(publisher, dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()