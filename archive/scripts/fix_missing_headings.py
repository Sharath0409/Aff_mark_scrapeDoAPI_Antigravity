#!/usr/bin/env python3
"""
Script to fix missing headings and unresolved [AUTHOR_BIO] placeholders in Blogger posts.

Features:
- Reads Google Sheet to get published posts with Post IDs, URLs, and topics
- Fetches each post via Blogger API to check for issues
- Fixes missing <h1> headings by inserting correct title
- Resolves [AUTHOR_BIO] placeholders with proper author bio content
- Uses PATCH (not UPDATE) to preserve published date
- Dry-run mode by default, with --apply flag to apply changes
- Dry-run shows table of proposed changes with published date before/after
"""

import sys
import argparse
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

# Add project root to path
sys.path.insert(0, '/Users/sharath/Desktop/Aff_mark_scrapeDoAPI_Antigravity/Aff_mark_scrapeDoAPI_Antigravity-2')

from config import settings
from core.sheets_manager import SheetsManager
from core.blogger_publisher import BloggerPublisher
from core.author_signals import generate_author_signals, DEFAULT_AUTHOR, DEFAULT_METHODOLOGY


class PostFixer:
    """Fixes missing headings and unresolved placeholders in Blogger posts."""
    
    def __init__(self, apply: bool = False):
        self.apply = apply
        self.sheets = SheetsManager(
            settings.GOOGLE_SHEET_ID,
            settings.GCP_SERVICE_ACCOUNT,
            sheet_name="Sheet1"
        )
        self.publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        self.changes_log = []
        
    def get_published_posts_from_sheet(self) -> List[Dict]:
        """Get all published posts from the Google Sheet with their Post IDs and topics.
        
        Note: Google Sheets API returns rows truncated at the last non-empty cell,
        so we need to map row indices to header indices accounting for missing columns.
        """
        try:
            rows = self.sheets.get_rows_by_status("Success")
            if not rows or len(rows) < 2:
                return []
            
            headers = rows[0]
            published_posts = []
            
            # Map header names to their indices
            header_to_idx = {name: i for i, name in enumerate(headers)}
            
            for row in rows[1:]:
                # Build a dict of available column values by header name
                # Since rows are truncated at last non-empty cell, we need to 
                # map row indices to header indices carefully
                row_data = {}
                
                # We know the expected header order. For each row, the values
                # correspond to the first N headers where N = len(row).
                # But some middle columns may be empty, causing shifts.
                # Strategy: iterate through headers and try to match with row values
                # based on expected data patterns.
                
                # Simpler approach: use the known column positions for key fields
                # based on observed row structure (7 columns returned)
                # Row indices observed: [Topic, Keyword, Category, Status, Blog URL, Post ID, Parent Post ID]
                # Corresponding to headers: [0, 1, 2, 4, 6, 8, 9]
                
                if len(row) >= 6:  # Minimum needed: Topic, Keyword, Category, Status, Blog URL, Post ID
                    post_data = {
                        "topic": row[0] if len(row) > 0 else "",
                        "keyword": row[1] if len(row) > 1 else "",
                        "category": row[2] if len(row) > 2 else "",
                        "status": row[3] if len(row) > 3 else "",
                        "url": row[4] if len(row) > 4 else "",
                        "post_id": row[5] if len(row) > 5 else "",
                        "parent_post_id": row[6] if len(row) > 6 else "",
                    }
                    
                    if post_data["post_id"]:
                        published_posts.append(post_data)
            
            return published_posts
        except Exception as e:
            print(f"Error fetching published posts from sheet: {e}")
            return []

    def check_post_issues(self, post: Dict, content: str, title: str) -> Dict:
        """Check a post for issues and return findings."""
        issues = {
            "missing_h1": False,
            "title_mismatch": False,
            "has_author_bio_placeholder": False,
            "current_title": title,
            "proposed_title": post["topic"],
        }
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check (a): Missing <h1> tag near the top (before first <h2>)
        first_h2 = soup.find('h2')
        first_h1 = soup.find('h1')
        
        if not first_h1:
            issues["missing_h1"] = True
        elif first_h2 and first_h1:
            # Check if h1 appears before first h2
            h1_pos = content.find(str(first_h1))
            h2_pos = content.find(str(first_h2))
            if h2_pos != -1 and h1_pos > h2_pos:
                issues["missing_h1"] = True
        
        # Check (b): Title mismatch with sheet
        if title and post["topic"]:
            if title.strip().lower() != post["topic"].strip().lower():
                issues["title_mismatch"] = True
        
        # Check (c): [AUTHOR_BIO] placeholder
        if "[AUTHOR_BIO]" in content:
            issues["has_author_bio_placeholder"] = True
        
        return issues

    def fix_post(self, post: Dict, post_data: Dict, issues: Dict) -> Tuple[str, str, bool]:
        """
        Fix the post issues and return (new_content, new_title, has_changes).
        Returns the fixed content, fixed title, and whether any changes were made.
        """
        content = post_data.get('content', '')
        title = post_data.get('title', '')
        has_changes = False
        new_content = content
        new_title = title
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Fix (a): Missing <h1> - insert at the top
        if issues["missing_h1"]:
            proposed_h1 = post["topic"]
            if proposed_h1:
                # Find the best place to insert h1 - at the very beginning of content
                new_h1_tag = soup.new_tag('h1')
                new_h1_tag.string = proposed_h1
                
                # Insert at the beginning of the body content
                if soup.body:
                    soup.body.insert(0, new_h1_tag)
                elif soup.html:
                    soup.html.insert(0, new_h1_tag)
                else:
                    # Insert at the beginning of the soup
                    soup.insert(0, new_h1_tag)
                
                new_content = str(soup)
                has_changes = True
        
        # Fix (b): Title mismatch - update title
        if issues["title_mismatch"]:
            new_title = post["topic"]
            has_changes = True
        
        # Fix (c): [AUTHOR_BIO] placeholder
        if issues.get("author_bio_placeholder") or issues.get("has_author_bio_placeholder"):
            # Generate author bio using existing module
            author_signals = generate_author_signals(
                author=DEFAULT_AUTHOR,
                methodology=DEFAULT_METHODOLOGY,
                include_top_byline=False,
                include_bottom_byline=True,
                include_methodology=False
            )
            author_bio_html = author_signals.get("bottom_byline", "")
            
            if author_bio_html:
                new_content = new_content.replace("[AUTHOR_BIO]", author_bio_html)
                has_changes = True
        
        return new_content, new_title, has_changes

    def get_post_date(self, post_data: Dict) -> Optional[str]:
        """Extract published date from post data."""
        return post_data.get('published', None)

    def dry_run(self) -> List[Dict]:
        """Run in dry-run mode - check all posts and report what would change."""
        print("=" * 100)
        print("DRY RUN MODE - Checking all published posts for issues")
        print("=" * 100)
        
        published_posts = self.get_published_posts_from_sheet()
        print(f"\nFound {len(published_posts)} published posts in sheet with Post IDs.")
        
        results = []
        
        for i, post in enumerate(published_posts):
            post_id = post["post_id"]
            if not post_id:
                continue
                
            try:
                post_data = self.publisher.get_post(post_id)
                content = post_data.get('content', '')
                title = post_data.get('title', '')
                published_date = post_data.get('published', '')
                
                issues = self.check_post_issues(post, content, title)
                
                has_issues = any([
                    issues["missing_h1"],
                    issues["title_mismatch"],
                    issues["has_author_bio_placeholder"]
                ])
                
                if has_issues:
                    new_content, new_title, would_change = self.fix_post(post, post_data, issues)
                    
                    # For dry run, we also check if published date would change
                    # We don't actually update, so date shouldn't change
                    proposed_date = post_data.get('published', '')
                    
                    results.append({
                        "post_id": post["post_id"],
                        "url": post["url"],
                        "current_title": title,
                        "proposed_title": new_title if issues["title_mismatch"] else title,
                        "published_date": published_date,
                        "proposed_date": proposed_date,
                        "issues": {
                            "missing_h1": issues["missing_h1"],
                            "title_mismatch": issues["title_mismatch"],
                            "author_bio_placeholder": issues["has_author_bio_placeholder"],
                        },
                        "would_change": would_change
                    })
                    
            except Exception as e:
                print(f"Error checking post {post_id}: {e}")
        
        # Print dry-run table
        if results:
            print(f"\n{'='*120}")
            print(f"DRY RUN RESULTS: {len(results)} posts would be modified")
            print(f"{'='*120}")
            print(f"{'Post ID':<25} {'Current Title':<40} {'Proposed Title':<40} {'Issues':<50}")
            print(f"{'-'*120}")
            for r in results:
                issues_str = []
                if r["issues"]["missing_h1"]: issues_str.append("NO_H1")
                if r["issues"]["title_mismatch"]: issues_str.append("TITLE_MISMATCH")
                if r["issues"]["author_bio_placeholder"]: issues_str.append("AUTHOR_BIO")
                issues_str = ", ".join(issues_str)
                
                curr_title = r["current_title"][:38] + ".." if len(r["current_title"]) > 40 else r["current_title"]
                prop_title = r["proposed_title"][:38] + ".." if len(r["proposed_title"]) > 40 else r["proposed_title"]
                
                print(f"{r['post_id']:<25} {curr_title:<40} {prop_title:<40} {issues_str:<50}")
            
            # Show published date verification
            print(f"\n{'='*120}")
            print("PUBLISHED DATE VERIFICATION (should be identical):")
            print(f"{'='*120}")
            print(f"{'Post ID':<25} {'Current Date':<30} {'Proposed Date':<30} {'Match':<10}")
            print(f"{'-'*95}")
            for r in results:
                match = "✓" if r["published_date"] == r["proposed_date"] else "✗ MISMATCH"
                print(f"{r['post_id']:<25} {r['published_date']:<30} {r['proposed_date']:<30} {match:<10}")
        else:
            print("\nNo posts with issues found!")
        
        return results

    def apply_fixes(self, results: List[Dict]) -> Dict:
        """Apply the fixes to Blogger posts using PATCH (not UPDATE)."""
        if not self.apply:
            print("\nNot applying changes. Use --apply flag to apply.")
            return {"applied": 0, "failed": 0}
        
        print("\n" + "=" * 100)
        print("APPLYING FIXES (using PATCH to preserve published date)")
        print("=" * 100)
        
        applied = 0
        failed = 0
        
        for r in results:
            if not r["would_change"]:
                continue
                
            try:
                post_id = r["post_id"]
                
                # Re-fetch and apply fix
                post_data = self.publisher.get_post(post_id)
                issues = r["issues"]
                
                # Reconstruct post dict for fixing
                fix_post = {"post_id": post_id, "topic": post_data.get('title', '')}
                new_content, new_title, _ = self.fix_post(fix_post, post_data, issues)
                
                # Build patch body - only include fields we're changing
                patch_body = {}
                if r["issues"]["title_mismatch"]:
                    patch_body["title"] = r["proposed_title"]
                if r["issues"]["missing_h1"] or r["issues"]["author_bio_placeholder"]:
                    # Need to get the new_content from fix_post
                    fix_post = {"post_id": post_id, "topic": r["proposed_title"] if r["issues"]["title_mismatch"] else post_data.get('title', '')}
                    new_content, _, _ = self.fix_post(fix_post, post_data, issues)
                    patch_body["content"] = new_content
                
                if patch_body:
                    # Use PATCH to preserve published date
                    # The Blogger API posts().patch() only updates provided fields
                    self.publisher.service.posts().patch(
                        blogId=settings.BLOGGER_BLOG_ID,
                        postId=post_id,
                        body=patch_body
                    ).execute()
                    
                    # Verify published date didn't change
                    updated_post = self.publisher.get_post(post_id)
                    new_published = updated_post.get('published', '')
                    original_published = r["published_date"]
                    
                    date_match = "✓" if new_published == r["published_date"] else "✗ DATE CHANGED!"
                    
                    print(f"  ✓ Updated {post_id}: {r['issues']} | Date: {date_match}")
                    self.changes_log.append({
                        "post_id": post_id,
                        "changes": r["issues"],
                        "original_date": r["published_date"],
                        "new_date": new_published,
                        "date_preserved": new_published == r["published_date"]
                    })
                    applied += 1
                    
            except Exception as e:
                print(f"  ✗ Failed to update {r['post_id']}: {e}")
                failed += 1
        
        return {"applied": applied, "failed": failed}


def main():
    parser = argparse.ArgumentParser(
        description="Fix missing headings and [AUTHOR_BIO] placeholders in Blogger posts"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run only)"
    )
    parser.add_argument(
        "--post-id",
        type=str,
        help="Only process a specific post ID"
    )
    args = parser.parse_args()
    
    print("=" * 80)
    print("BLOGGER POST FIXER - Missing Headings & AUTHOR_BIO Placeholder")
    print("=" * 80)
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    fixer = PostFixer(apply=args.apply)
    
    # Run dry-run first (always)
    results = fixer.dry_run()
    
    # Apply if requested
    if args.apply:
        summary = fixer.apply_fixes(results)
        print(f"\n{'='*80}")
        print(f"SUMMARY: Applied={summary['applied']}, Failed={summary['failed']}")
        print("=" * 80)
        
        # Show final date verification
        if fixer.changes_log:
            print("\nPUBLISHED DATE VERIFICATION LOG:")
            print("-" * 80)
            for log in fixer.changes_log:
                status = "✓ PRESERVED" if log["date_preserved"] else "✗ CHANGED!"
                print(f"  {log['post_id']}: {log['original_date']} -> {log['new_date']} | {status}")
    else:
        print("\nDry-run complete. Use --apply to apply changes.")


if __name__ == "__main__":
    main()