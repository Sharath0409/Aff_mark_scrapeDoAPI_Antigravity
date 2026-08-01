#!/usr/bin/env python3
"""
Migration script: Add <!--more--> jump break to ALL existing Blogger posts.
Uses the same logic as new post generation (insert after first meaningful paragraph).
Run once to fix all existing posts.
"""

import sys
import time
from config import settings
from core.blogger_publisher import BloggerPublisher, insert_jump_break_after_first_paragraph

def migrate_all_posts():
    publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
    
    print("Fetching all posts...")
    posts = publisher.list_all_posts(max_results=500)
    print(f"Found {len(posts)} posts. Processing...")
    
    updated = 0
    skipped = 0
    errors = 0
    
    for i, post in enumerate(posts):
        post_id = post['id']
        title = post['title']
        
        # Fetch full content
        full_post = publisher.get_post(post_id)
        content = full_post.get('content', '')
        
        # Check if already has jump break
        if '<!--more-->' in content:
            print(f"  [{i+1}/{len(posts)}] SKIP (already has jump break): {title[:60]}")
            skipped += 1
            continue
        
        # Apply jump break insertion
        new_content = insert_jump_break_after_first_paragraph(content)
        
        # Verify change was made
        if new_content == content:
            print(f"  [{i+1}/{len(posts)}] SKIP (no change): {title[:60]}")
            skipped += 1
            continue
        
        # Update post
        try:
            publisher.update_post(post_id, {"content": new_content})
            print(f"  [{i+1}/{len(posts)}] UPDATED: {title[:60]}")
            updated += 1
        except Exception as e:
            print(f"  [{i+1}/{len(posts)}] ERROR: {title[:60]} - {e}")
            errors += 1
        
        # Rate limiting: small delay to avoid API quotas
        time.sleep(0.5)
    
    print(f"\n=== MIGRATION COMPLETE ===")
    print(f"Total posts: {len(posts)}")
    print(f"Updated: {updated}")
    print(f"Skipped (already had jump break or no change): {skipped}")
    print(f"Errors: {errors}")

if __name__ == '__main__':
    migrate_all_posts()
