# Plan: Complete Informational Workflow (Steps 7-12)

## Objective
Complete the informational publishing workflow in `main_informational.py` by implementing the remaining stages (Steps 7-12) to make it production-ready, while strictly reusing existing architecture components.

## Current State (Steps 1-6 Complete)
- ✅ Read Pending Topic from `Informational_Topics` worksheet
- ✅ Mark row as "Processing" 
- ✅ Generate Blueprint (`generate_informational_blueprint`)
- ✅ Generate Complete Article (`generate_informational_article`)
- ✅ Generate Image Plan (`generate_image_plan`)
- ✅ Generate AI Images, Optimize, Upload to GCS (`generate_article_images`)
- ✅ Generate Image Manifest
- ✅ Inject Images into Article (`inject_images_into_article`)

## Required Implementation (Steps 7-12)

### Step 7: Blogger Publishing
**File:** `main_informational.py`
- Reuse `BloggerPublisher.publish_post(title, content, labels)`
- Generate SEO labels using existing `ContentGenerator.generate_seo_tags(topic, keyword)`
- Receive: `published_url`, `post_id`

### Step 8: Success/Failure Handling
**File:** `main_informational.py`
- Wrap entire workflow in try/except (following commercial pattern in `main.py`)
- On success: store `published_url`, `post_id`
- On failure: capture error message + stack trace (logger only)

### Step 9: Google Sheets Updates
**File:** `main_informational.py`
- Reuse `SheetsManager.update_row_status(row_index, "Success", url=published_url, post_id=post_id)`
- Reuse `SheetsManager.update_dashboard_stats("Success")`
- Reuse `SheetsManager.log_execution(topic, "Success", url=published_url)`

### Step 10: Execution Logging
**File:** `main_informational.py`
- Reuse existing logger (`get_logger("main_informational")`)
- Log start/completion of each major stage
- Use existing log format

### Step 11: Email Notifications
**File:** `main_informational.py`
- Reuse `EmailNotifier.send_report()`
- Success: Topic, Published URL, Post ID
- Failure: Topic, Failure Reason

### Step 12: Resource Cleanup
**File:** `main_informational.py`
- Reuse `ImageOptimizer.cleanup()` in finally block

---

## Missing Methods in ContentGenerator

The following methods are called from `main_informational.py` but don't exist in `ContentGenerator` yet. They need to be implemented by reusing existing patterns:

1. **`generate_informational_blueprint(topic, keyword, category)`** - Uses `INFORMATIONAL_BLUEPRINT_TEMPLATE` + `generate_section()`
2. **`generate_informational_article(blueprint, topic, keyword, category)`** - Uses `INFORMATIONAL_ARTICLE_TEMPLATE` + `generate_section()`
3. **`generate_image_plan(blueprint, article, topic, keyword, category)`** - Uses `INFORMATIONAL_IMAGE_PLAN_TEMPLATE` + `generate_section()`
4. **`generate_article_images(image_plan, topic)`** - Parse image plan, generate/optimize/upload each image, return manifest
5. **`inject_images_into_article(article, image_manifest)`** - Inject images into HTML using BeautifulSoup

---

## Implementation Strategy

### Modify `core/content_generator.py`
Add the 5 missing methods following existing patterns:
- Use `self.client.chat.completions.create()` with `SYSTEM_PROMPT`
- Use `self.generate_section()` with retry decorator
- Reuse existing `ImageOptimizer`, `BloggerCDNUploader`, `settings.GCS_BUCKET_NAME`
- Reuse `generate_section()` for all LLM calls
- Return parsed results (JSON for image plan, list for manifest)

### Modify `main_informational.py`
Complete the workflow by adding:
1. Internal linking via `InternalLinkManager.link_informational_article()`
2. Blogger publishing via `BloggerPublisher.publish_post()`
3. SEO labels via `ContentGenerator.generate_seo_tags()`
4. Google Sheets updates via `SheetsManager` methods
4. Email notification via `EmailNotifier`
5. Cleanup via `ImageOptimizer.cleanup()`
6. Full try/except with logging

---

## Files to Modify

1. **`core/content_generator.py`** - Add 5 missing methods
2. **`main_informational.py`** - Complete workflow (Steps 7-12)

---

## Architecture Compliance Checklist

- [ ] No new BloggerPublisher - reuse existing
- [ ] No new SheetsManager - reuse existing
- [ ] No new EmailNotifier - reuse existing
- [ ] No new InternalLinkManager - reuse existing
- [ ] No new ContentGenerator - extend existing
- [ ] No new Logger - reuse `get_logger()`
- [ ] No new Retry system - reuse `get_retry_decorator()`
- [ ] No new OpenAI/Deepseek client - reuse `DeepseekHttpClient`
- [ ] No duplicate prompts - use existing templates
- [ ] Commercial workflow untouched
- [ ] No file moves/renames
- [ ] No new abstractions

---

## Validation

Test the workflow:
1. Dry run with a pending topic in `Informational_Topics`
2. Verify all stages log correctly
3. Verify Blogger post published
4. Verify Google Sheet updated
5. Verify email sent
6. Verify temp files cleaned up