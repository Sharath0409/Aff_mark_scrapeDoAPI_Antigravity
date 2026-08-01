# Implementation Plan: Jump Breaks, Audit Script, and Draft-to-Publish Workflow

## Overview
Three related fixes to address inconsistent homepage previews and mid-generation crashes leaving broken posts live.

---

## CHANGE 1: Add `<!--more-->` Jump Break During HTML Generation

### Problem
Currently `insert_jump_break()` is called at publish time in `BloggerPublisher.publish_post()` and `update_post()`. This means:
- If Stage 3 publishes then Stage 4 crashes, the post is live without a jump break
- The jump break logic runs AFTER internal linking, not during generation
- No guaranteed first-paragraph break in the generated HTML body

### Solution
Add `<!--more-->` during HTML generation (Stage 2) in `ContentGenerator.generate_informational_article()` and `generate_full_post()`, so the jump break is baked into the HTML body from the start.

### Files to Modify
1. **`core/content_generator.py`** - Add jump break insertion after first paragraph in:
   - `generate_informational_article()` (line 999)
   - `generate_full_post()` (line ~103 in pipeline.py calls this)

2. **`core/blogger_publisher.py`** - Modify `insert_jump_break()` to be a public utility that can be called during generation, not just at publish time. Keep existing publish-time call as safety net.

### Implementation Details
- Create a new utility function `insert_jump_break_after_first_paragraph(html)` in `blogger_publisher.py` (or new utility module) that:
  - Finds the first `<p>` tag after any introductory content
  - Inserts `<!--more-->` after it
  - Returns modified HTML
- Call this at the end of `generate_informational_article()` and `generate_full_post()`

---

## CHANGE 2: Create Audit Script for Broken Posts

### Problem
Posts that crashed during Stage 4 (images) or Stage 5 (internal linking) are left live with:
- Unresolved `[IMG-N]` markers
- Missing `<!--more-->` tags
- Truncated/short body content

### Solution
Create standalone audit script `scripts/audit_broken_posts.py` that:
1. Uses existing `BloggerPublisher` to fetch ALL published posts (with bodies)
2. Checks each post for:
   - **Leftover `[IMG-` markers** → regex `\[IMG-\d+\]`
   - **Missing `<!--more-->`** → string search
   - **Suspiciously short body** → text length < 1000 chars (configurable threshold)
3. Outputs CSV: `title,url,post_id,issues_found,body_length`
4. **Read-only** - no modifications, just reporting

### Files to Create
- **`scripts/audit_broken_posts.py`** - New standalone audit script

### Implementation Details
- Use `BloggerPublisher.list_all_posts(max_results=500)` with `fetchBodies=True`
- For each post, fetch full body via `get_post(post_id)`
- Run checks, accumulate results
- Write CSV to `audit_report_YYYYMMDD.csv`
- Print summary to console

---

## CHANGE 3: Stage 3 Publish as Draft, Flip to Live After Stage 5

### Problem
Stage 3 publishes live immediately. If Stage 4 or 5 crashes, the post is live in broken state.

### Solution
Two-phase publish:
1. **Stage 3**: Publish as **draft** (`isDraft=True`)
2. **Stage 6**: After Stage 4 (images) AND Stage 5 (internal linking) complete successfully, flip to live (`isDraft=False`)

### Files to Modify

#### 1. `core/blogger_publisher.py`
- Add `isDraft` parameter to `publish_post()` (default `False` for backward compat)
- Add `set_post_status(post_id, isDraft)` method to flip draft/live status
- Update `publish_post()` to accept `isDraft` parameter

#### 2. `main_informational.py` (Informational Workflow)
- **Stage 3**: Call `publish_post(..., isDraft=True)` → get post_id
- **Stage 4**: Generate images, update post content (still draft)
- **Stage 5**: Internal linking, update post content (still draft)
- **Stage 6**: Call `set_post_status(post_id, isDraft=False)` to go live
- Update Sheets status only after going live

#### 3. `core/pipeline.py` (Commercial Workflow)
- Same pattern: publish as draft, flip to live after internal linking
- Since commercial workflow is single-script, restructure `process_row()`:
  1. Generate content
  2. Publish as draft
  3. Internal linking (update draft)
  4. Flip to live
  5. Update Sheets

### Rollback Safety
- If any stage fails, the draft remains unpublished
- Sheets status stays "Processing" or "Failed" - never "Success" for partial posts
- No manual cleanup needed for crashed posts

---

## IMPLEMENTATION ORDER

### Phase 1: Core Utilities (no workflow changes)
1. Add `insert_jump_break_after_first_paragraph()` to `blogger_publisher.py`
2. Call it in `ContentGenerator.generate_informational_article()` and `generate_full_post()`

### Phase 2: Draft-to-Publish Workflow
1. Update `BloggerPublisher` with `isDraft` parameter and `set_post_status()`
2. Update `main_informational.py` for draft→live flow
3. Update `core/pipeline.py` for commercial workflow draft→live flow

### Phase 3: Audit Script
1. Create `scripts/audit_broken_posts.py`
2. Test against current Blogger posts

---

## DETAILED CODE CHANGES

### File: `core/blogger_publisher.py`

**Add new utility function:**
```python
def insert_jump_break_after_first_paragraph(html: str) -> str:
    """Insert <!--more--> after the first clean paragraph in generated HTML."""
    if not html or '<!--more-->' in html:
        return html
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find first <p> tag that has meaningful content (not just whitespace)
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 50:  # Meaningful paragraph
            p.insert_after(Comment('more'))
            return str(soup)
    
    # Fallback: insert before first H2 if no substantial paragraph
    first_h2 = soup.find('h2')
    if first_h2:
        first_h2.insert_before(Comment('more'))
        return str(soup)
    
    # Last resort: append at end
    soup.append(Comment('more'))
    return str(soup)
```

**Modify `publish_post()`:**
```python
def publish_post(self, title, content, labels=None, isDraft=False):
    # ... existing code ...
    body = {
        "kind": "blogger#post",
        "title": title,
        "content": content,
        "labels": labels or []
    }
    request = posts.insert(blogId=self.blog_id, body=body, isDraft=isDraft)
    # ...
```

**Add new method:**
```python
@get_retry_decorator()
def set_post_status(self, post_id: str, isDraft: bool):
    """Flip a post between draft and live status."""
    post = self.get_post(post_id)
    post['status'] = 'DRAFT' if isDraft else 'LIVE'
    return self.service.posts().update(blogId=self.blog_id, postId=post_id, body=post).execute()
```

---

### File: `core/content_generator.py`

**Modify `generate_informational_article()`:**
```python
def generate_informational_article(self, blueprint: str, topic: str, keyword: str, category: str) -> str:
    # ... existing code ...
    article_html = self.generate_section(prompt, model="gpt-4o-mini")
    # Clean markdown
    if article_html.startswith("```html"):
        article_html = article_html.split("```html")[1].split("```")[0].strip()
    elif article_html.startswith("```"):
        article_html = article_html.split("```")[1].split("```")[0].strip()
    
    # ADD JUMP BREAK AFTER FIRST PARAGRAPH
    from core.blogger_publisher import insert_jump_break_after_first_paragraph
    article_html = insert_jump_break_after_first_paragraph(article_html)
    
    return sanitize_html(article_html)
```

**Also add to `generate_full_post()`** (called from pipeline.py)

---

### File: `main_informational.py` - Draft-to-Live Workflow

**Stage 3 (Publish as Draft):**
```python
# --- STAGE 3: Publish as DRAFT to get Blogger Post ID ---
logger.info("Stage 3/7: Publishing to Blogger as DRAFT to get Post ID")
print("--- STAGE 3: Publishing to Blogger as DRAFT (get Post ID) ---")
seo_labels = generator.generate_seo_tags(topic, keyword)
if category not in seo_labels:
    seo_labels.append(category)

published_url, post_id = publisher.publish_post(topic, article_with_markers, labels=seo_labels, isDraft=True)
logger.info(f"Article published as DRAFT: {published_url} (Post ID: {post_id})")
print(f"Published as DRAFT: {published_url}")
print(f"Post ID: {post_id}\n")
```

**Stage 6 (Flip to Live):**
```python
# --- STAGE 6: Flip to LIVE and Update Blogger Post with Internal Links ---
logger.info("Stage 6/7: Flipping post to LIVE with internal links")
print("--- STAGE 6: Flipping Post to LIVE with Internal Links ---")
publisher.set_post_status(post_id, isDraft=False)
publisher.update_post(post_id, {"content": final_html, "labels": seo_labels})
logger.info("Blogger post flipped to LIVE with internal links")
print("Blogger post flipped to LIVE with internal links.\n")
```

**Move Sheets update to AFTER going live:**
```python
# --- STAGE 7: Google Sheets Updates (ONLY after LIVE) ---
logger.info("Stage 7/7: Updating Google Sheets")
print("--- STAGE 7: Updating Google Sheets ---")
sheets.update_row_status(row_index, "Success", url=published_url, post_id=post_id)
sheets.update_dashboard_stats("Success")
sheets.log_execution(topic, "Success", url=published_url)
```

---

### File: `core/pipeline.py` - Commercial Workflow Draft-to-Live

```python
def process_row(...):
    # ... existing code up to content generation ...
    
    # 7. Publish to Blogger as DRAFT
    clean_title = topic.strip()
    published_url, current_post_id = publisher.publish_post(clean_title, cleaned_content, labels=seo_labels, isDraft=True)
    
    # 8. Internal Linking (on draft)
    related_posts = link_manager.get_related_articles(topic, seo_labels, count=3)
    if related_posts:
        cleaned_content = link_manager.inject_internal_links(cleaned_content, related_posts)
        cleaned_content = link_manager.add_related_section(cleaned_content, related_posts)
        publisher.update_post(current_post_id, {"content": cleaned_content, "labels": seo_labels})
    
    # 9. Flip to LIVE
    publisher.set_post_status(current_post_id, isDraft=False)
    
    # 10. Update Google Sheets (only after LIVE)
    sheets.update_row_status(row_index, "Success", url=published_url, post_id=current_post_id, product_count=len(products_data))
    # ...
```

---

## AUDIT SCRIPT: `scripts/audit_broken_posts.py`

```python
#!/usr/bin/env python3
"""Audit Blogger posts for broken content: leftover [IMG- markers, missing <!--more-->, short bodies."""

import sys
import csv
import re
from datetime import datetime
from config import settings
from core.blogger_publisher import BloggerPublisher

def check_post(post):
    """Check a single post for issues. Returns list of issue strings."""
    issues = []
    content = post.get('content', '')
    text_content = content  # We'll use raw HTML for marker checks
    
    # Check 1: Leftover [IMG-N] markers
    img_markers = re.findall(r'\[IMG-\d+\]', content)
    if img_markers:
        issues.append(f"leftover_img_markers:{len(img_markers)}")
    
    # Check 2: Missing <!--more-->
    if '<!--more-->' not in content:
        issues.append("missing_more_tag")
    
    # Check 3: Suspiciously short body
    # Use text content for length check
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')
    text_length = len(soup.get_text(strip=True))
    if text_length < 1000:
        issues.append(f"short_body:{text_length}chars")
    
    return issues, text_length

def main():
    publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
    
    print("Fetching all published posts...")
    posts = publisher.list_all_posts(max_results=500)
    print(f"Found {len(posts)} posts. Fetching full content...")
    
    flagged = []
    for i, post in enumerate(posts):
        if i % 50 == 0:
            print(f"  Checking post {i+1}/{len(posts)}: {post['title'][:60]}")
        
        # Fetch full body
        full_post = publisher.get_post(post['id'])
        content = full_post.get('content', '')
        
        issues, body_len = check_post(full_post)
        
        if issues:
            flagged.append({
                'title': post['title'],
                'url': post['url'],
                'post_id': post['id'],
                'issues': ';'.join(issues),
                'body_length': body_len
            })
    
    # Write CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f"audit_report_{timestamp}.csv"
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'url', 'post_id', 'issues', 'body_length'])
        writer.writeheader()
        writer.writerows(flagged)
    
    print(f"\n=== AUDIT COMPLETE ===")
    print(f"Total posts checked: {len(posts)}")
    print(f"Flagged posts: {len(flagged)}")
    print(f"Report saved to: {csv_file}")
    
    if flagged:
        print("\nFlagged posts:")
        for p in flagged[:10]:
            print(f"  - {p['title'][:60]} | {p['issues']} | {p['body_length']} chars")
        if len(flagged) > 10:
            print(f"  ... and {len(flagged) - 10} more")

if __name__ == '__main__':
    main()
```

---

## TESTING CHECKLIST

### For Jump Break (Change 1)
- [ ] Generate informational article → verify `<!--more-->` after first paragraph
- [ ] Generate commercial article → verify `<!--more-->` present
- [ ] Verify existing `insert_jump_break()` at publish time doesn't duplicate

### For Draft-to-Live (Change 3)
- [ ] Informational: Stage 3 publishes draft, Stage 6 flips to live
- [ ] Commercial: Pipeline publishes draft, flips live after linking
- [ ] If Stage 4 crashes → post stays draft, never public
- [ ] Sheets only updated after live flip

### For Audit Script (Change 2)
- [ ] Script runs without modifying any posts
- [ ] CSV output has correct columns
- [ ] Correctly flags posts with `[IMG-` markers
- [ ] Correctly flags missing `<!--more-->`
- [ ] Correctly flags short bodies

---

## RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| Draft posts accumulate if workflow crashes | Sheets status stays "Processing"; manual cleanup documented |
| Jump break inserted in wrong place | Unit test with various HTML structures |
| Blogger API rate limits on audit | Add small delay between `get_post` calls |
| Existing live posts without jump break | Audit script identifies them for manual fix |

---

## FILES TO MODIFY SUMMARY

| File | Changes |
|------|---------|
| `core/blogger_publisher.py` | Add `insert_jump_break_after_first_paragraph()`, add `isDraft` param to `publish_post()`, add `set_post_status()` |
| `core/content_generator.py` | Call jump break insertion in `generate_informational_article()` and `generate_full_post()` |
| `main_informational.py` | Restructure Stages 3-6 for draft→live flow |
| `core/pipeline.py` | Restructure `process_row()` for draft→live flow |
| `scripts/audit_broken_posts.py` | **NEW FILE** - standalone audit script |

---

## IMPLEMENTATION PRIORITY

1. **Phase 1**: Jump break utility + integration (Changes 1)
2. **Phase 2**: Draft→Live workflow for both workflows (Change 3)
3. **Phase 4**: Audit script (Change 2) - can run independently

Each phase can be tested independently before moving to the next.