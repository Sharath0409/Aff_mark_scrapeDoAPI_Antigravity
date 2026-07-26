# Plan: Enhance Posts Update Workflow to Full Regeneration

## Objective
Extend the existing Posts Update workflow (`scripts/daily_published_review.py`) to completely regenerate older articles using the current production pipeline standards, while preserving Blogger Post ID, URL, analytics, and comments.

## Current State
- `scripts/daily_published_review.py` - Entry point, calls `run_review()` from `content_reviewer.py`
- `core/content_reviewer.py` - Currently only does drift detection/correction
- `core/pipeline.py` - Contains `process_row()` which is the production pipeline
- `core/content_generator.py` - Has `generate_full_post()` for 5-product reviews

## Implementation Plan

### 1. Modify `core/content_reviewer.py`
Add a new function `regenerate_post()` that:
- Takes a post from Blogger and its corresponding sheet row
- Uses the production pipeline components to completely regenerate the article
- Updates the existing Blogger post in place (preserving ID/URL)
- Updates Google Sheets with refreshed status

Key components to reuse from `core/pipeline.py`:
- `AmazonScraper` for product scraping
- `ContentGenerator.generate_full_post()` for 5-product content
- `InternalLinkManager` for internal linking
- `BloggerPublisher.update_post()` to preserve ID/URL
- `ImageOptimizer` + `BloggerCDNUploader` for images
- `SheetsManager` for status updates

### 2. Modify `scripts/daily_published_review.py`
- Add a `--regenerate` flag to trigger full regeneration instead of drift detection
- Call the new `regenerate_post()` function for each selected post

### 3. Add helper to find sheet row for a post
- Need to look up the original sheet row by topic to get keyword/category
- Reuse `SheetsManager.get_all_rows()` and match by topic

## Files to Modify
1. `core/content_reviewer.py` - Add `regenerate_post()` function and `run_regeneration()` 
2. `scripts/daily_published_review.py` - Add `--regenerate` flag and call new function

## Architecture Compliance
- ✅ Reuses existing production components (no new modules)
- ✅ Preserves Blogger Post ID, URL, analytics, comments
- ✅ No changes to commercial publishing workflow (`main.py`, `run_batch.py`)
- ✅ No new abstractions - extends existing workflow