#!/usr/bin/env python3
"""
Audit script: Fetches all published Blogger posts and flags broken content.
Checks for:
(a) Literal # at start of heading-like lines (unconverted markdown)
(b) Missing <!--more--> tag with very short visible body length
Outputs CSV with title, URL, Post ID, and detected issues.
"""

import sys
import csv
import re
from datetime import datetime
from bs4 import BeautifulSoup

# Add project root to path
sys.path.insert(0, '/Users/sharath/Desktop/Aff_mark_scrapeDoAPI_Antigravity/Aff_mark_scrapeDoAPI_Antigravity-2')

from config import settings
from core.blogger_publisher import BloggerPublisher


def check_post_for_issues(post, content):
    """
    Check a single post for issues.
    Returns list of issue strings found.
    """
    issues = []
    
    # Parse HTML
    soup = BeautifulSoup(content, 'html.parser')
    text_content = soup.get_text(strip=True)
    
    # Check (a): Literal # at start of heading-like lines (unconverted markdown)
    # Look for lines starting with # followed by space, not inside HTML tags
    lines = content.split('\n')
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('#') and ' ' in stripped[:7]:  # # followed by space within first 7 chars
            # Check if this is inside an HTML tag (false positive protection)
            if not re.search(r'<[^>]*>', line):
                issues.append(f"unconverted_markdown_heading_line_{i+1}: {stripped[:80]}")
    
    # Check (b): Missing <!--more--> tag
    if '<!--more-->' not in content:
        issues.append("missing_more_tag")
    
    # Check (c): Very short visible body length (crash-interrupted post)
    # Get visible text length (excluding HTML tags)
    text_length = len(text_content)
    if text_length < 500:  # Threshold for "suspiciously short"
        issues.append(f"short_body:{len(text_content)}chars")
    
    return issues


def main():
    from config import settings
    
    publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
    
    print("Fetching all published posts...")
    posts = publisher.list_all_posts(max_results=500, fetch_bodies=True)
    print(f"Found {len(posts)} posts. Checking for issues...")
    
    flagged_posts = []
    
    for i, post in enumerate(posts):
        if i % 20 == 0:
            print(f"  Checking post {i+1}/{len(posts)}: {post['title'][:60]}")
        
        content = post.get('content', '')
        
        issues = check_post_for_issues(post, content)
        
        if issues:
            # Get body text length for reporting
            soup = BeautifulSoup(post.get('content', ''), 'html.parser')
            text_length = len(soup.get_text(strip=True))
            
            flagged_posts.append({
                'title': post['title'],
                'url': post['url'],
                'post_id': post['id'],
                'issues': '; '.join(issues),
                'body_length': len(BeautifulSoup(post.get('content', ''), 'html.parser').get_text(strip=True))
            })
    
    # Write CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f"audit_report_{timestamp}.csv"
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'url', 'post_id', 'issues', 'body_length'])
        writer.writeheader()
        writer.writerows(flagged_posts)
    
    print(f"\n=== AUDIT COMPLETE ===")
    print(f"Total posts checked: {len(posts)}")
    print(f"Flagged posts: {len(flagged_posts)}")
    print(f"Report saved to: {csv_file}")
    
    if flagged_posts:
        print("\nFlagged posts:")
        for p in flagged_posts:
            print(f"  - {p['title'][:60]} | {p['issues']} | {p['body_length']} chars")
        if len(flagged_posts) > 10:
            print(f"  ... and {len(flagged_posts) - 10} more")
    
    # Sanity check: Look for "Complete Remote Work Guide" specifically
    print("\n=== SANITY CHECK: 'Complete Remote Work Guide' ===")
    for post in posts:
        if 'Complete Remote Work Guide' in post['title']:
            content = post.get('content', '')
            issues = check_post_for_issues(post, content)
            print(f"  Found post: {post['title']}")
            print(f"  Post ID: {post['id']}")
            print(f"  URL: {post['url']}")
            print(f"  Issues found: {issues if issues else 'NONE'}")
            soup = BeautifulSoup(content, 'html.parser')
            print(f"  Body length: {len(BeautifulSoup(post.get('content', ''), 'html.parser').get_text(strip=True))} chars")
            print(f"  Has <!--more-->: {'<!--more-->' in content}")
            # Check for literal # in content
            if '# ' in content or '#\n' in content or re.search(r'#\s+\w', content):
                print(f"  WARNING: Contains literal '# ' pattern (possible unconverted markdown)")
            break
    else:
        print("  'Complete Remote Work Guide' post NOT FOUND in published posts!")


if __name__ == '__main__':
    from datetime import datetime
    main()