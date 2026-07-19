# Fix High & Medium Priority Issues Plan

## Overview
This plan addresses all high and medium priority issues identified in the RemoteProstor codebase across core modules, scripts, and workflows.

---

## HIGH PRIORITY ISSUES

### 1. Function Signature Mismatch - `expand_old_posts.py` → `post_product_expander.py`
**File:** `scripts/expand_old_posts.py:67`  
**Issue:** Calls `expand_post(publisher, generator, scraper, sheets, post)` with 5 args, but `expand_post()` in `core/post_product_expander.py:234` only accepts 4 params `(publisher, generator, sheets, post)`.  
**Fix:** Remove `scraper` from the call since `expand_post` creates its own `AmazonScraper` internally in `_scrape_new_products()`.

### 2. Hardcoded Row Range in `run_batch.py`
**File:** `scripts/run_batch.py:152-153`  
**Issue:** `start_row = 79` and `end_row = 89` are hardcoded.  
**Fix:** Add `--start-row` and `--end-row` CLI arguments (default to current values for backward compatibility).

### 3. ImageOptimizer Cleanup Not Guaranteed on Exceptions
**Files:** `main.py:138`, `scripts/run_batch.py:200`, `core/post_product_expander.py:299`  
**Issue:** `optimizer.cleanup()` called after success but not in `finally` blocks. Temp files leak on exceptions.  
**Fix:** Wrap processing in `try/finally` to ensure `cleanup()` always runs.

### 4. Duplicate Row Processing Logic Between `main.py` and `run_batch.py`
**Files:** `main.py:18-156`, `scripts/run_batch.py:23-112`  
**Issue:** ~90 lines of nearly identical code for processing a single row.  
**Fix:** Extract shared logic into `core/pipeline.py` with a `process_row()` function used by both entry points.

---

## MEDIUM PRIORITY ISSUES

### 5. Fragile Regex in InternalLinkManager
**File:** `core/internal_linker.py:61`  
**Issue:** `indices = [int(i) for i in re.findall(r'\d+', content)]` matches ANY digits in LLM response, not just indices.  
**Fix:** Use explicit JSON array parsing or a more specific regex like `r'\[(\d+(?:,\s*\d+)*)\]'`.

### 6. No Content Validation Before Blogger Publish
**Files:** `main.py:130`, `scripts/run_batch.py:104`, `core/post_product_expander.py:319`  
**Issue:** Could publish empty/malformed HTML.  
**Fix:** Add validation in `BloggerPublisher.publish_post()` and `update_post()` to verify content length > 100 chars and contains required elements.

### 7. Cannibalization Checker Not in Daily Workflow
**File:** `.github/workflows/daily_maintenance.yml`  
**Issue:** `check_cannibalization.py` exists but isn't scheduled.  
**Fix:** Add `cannibalize` job to `daily_maintenance.yml` running weekly (e.g., Sundays 14:00 UTC).

### 8. Hardcoded Model in ContentReviewer
**File:** `core/content_reviewer.py:117`  
**Issue:** `model="deepseek-v4-flash"` hardcoded.  
**Fix:** Add `model` parameter to `review_post()` and `run_review()`, default from settings.

### 9. Inconsistent Error Handling Patterns
**Files:** Multiple  
**Issue:** Some catch `Exception`, others catch specific errors, some don't log stack traces.  
**Fix:** Standardize on catching `Exception` with `exc_info=True` for logging, re-raise only when caller should handle.

### 10. Missing Type Hints in Internal Functions
**File:** `core/post_product_expander.py`  
**Issue:** Functions like `_extract_asin_from_url`, `_get_existing_asins`, `_count_product_sections`, `_get_keyword_from_sheet`, `_scrape_new_products`, `_generate_review_section`, `_inject_product_sections` lack type hints.  
**Fix:** Add full type annotations.

### 11. No Unit Tests
**Issue:** Zero test files in codebase.  
**Fix:** Add `tests/` directory with pytest fixtures for core modules (scraper, content_generator, sheets_manager, cannibalization_checker).

### 12. SheetsManager Hardcoded Default Sheet Name
**File:** `core/sheets_manager.py:10`  
**Issue:** Default `sheet_name="Sheet1"` but informational workflow uses "Informational_Topics".  
**Fix:** Make sheet_name required (remove default) or add config constant.

### 13. Library Modules Don't Configure Logging
**Files:** All `core/*.py` using `get_logger(__name__)`  
**Issue:** Scripts configure logging but library modules don't propagate to root.  
**Fix:** Ensure `config/logger.py` configures root logger on import, or document that scripts must call `logging.basicConfig()` first.

### 14. PostProductExpander Creates New Optimizer/Uploader Per Post
**File:** `core/post_product_expander.py:284-285`  
**Issue:** `optimizer = ImageOptimizer()`, `uploader = BloggerCDNUploader(...)` created inside `expand_post()` loop.  
**Fix:** Pass pre-created instances as parameters (like `main.py` does).

### 15. expand_old_posts.py Creates Unused Scraper in Dry-Run
**File:** `scripts/expand_old_posts.py:57-58`  
**Issue:** `scraper = AmazonScraper()` created but not used in dry-run mode.  
**Fix:** Move scraper initialization inside `if args.apply:` block.

### 16. Inline run_single_row in main.py Should Be Shared
**File:** `main.py:18-156`  
**Issue:** `main()` contains all logic inline; `run_batch.py` has separate `run_single_row()`.  
**Fix:** Part of Issue #4 - extract to `core/pipeline.py`.

### 17. Missing Retry for Scrape.do API Calls
**File:** `core/scraper.py:38` has `@get_retry_decorator()` but `_fetch_via_scraped()` (line 19) doesn't.  
**Fix:** Add retry decorator to `_fetch_via_scraped()`.

### 18. Settings Validation Only Prints Warning
**File:** `config/settings.py:26-28`  
**Issue:** Missing required env vars only print warning, don't fail fast.  
**Fix:** Raise `RuntimeError` for missing REQUIRED_SETTINGS in production (not tests).

---

## IMPLEMENTATION ORDER

### Phase 1: Critical Bug Fixes (High Priority)
1. Fix function signature mismatch (Issue #1)
2. Add CLI args for row range (Issue #2)
3. Ensure optimizer cleanup in finally blocks (Issue #3)
4. Extract shared pipeline logic (Issue #4)

### Phase 2: Robustness & Quality (Medium Priority)
5. Fix fragile regex (Issue #5)
6. Add content validation (Issue #6)
7. Add cannibalization job to workflow (Issue #7)
8. Make model configurable (Issue #8)
9. Standardize error handling (Issue #9)
10. Add type hints (Issue #10)

### Phase 3: Infrastructure (Medium Priority)
11. Add unit test structure (Issue #11)
12. Fix SheetsManager default (Issue #12)
13. Fix logging configuration (Issue #13)
14. Reuse optimizer/uploader instances (Issue #14)
15. Lazy scraper init (Issue #15)
16. Add retry to _fetch_via_scraped (Issue #17)
17. Fail-fast settings validation (Issue #18)

---

## VALIDATION PLAN

After each phase:
1. Run `python scripts/expand_old_posts.py --apply` (dry-run first) to verify Issue #1 fix
2. Run `python scripts/run_batch.py --start-row 1 --end-row 1` to verify Issue #2
3. Run `python main.py` with mocked services to verify no temp file leaks (Issue #3)
4. Verify both `main.py` and `run_batch.py` produce identical results (Issue #4)
5. Run cannibalization script manually to verify workflow integration (Issue #7)
6. Run any existing lint/typecheck commands

---

## FILES TO MODIFY

| File | Issues Addressed |
|------|-----------------|
| `scripts/expand_old_posts.py` | #1, #15 |
| `scripts/run_batch.py` | #2, #3, #4, #16 |
| `main.py` | #3, #4, #16 |
| `core/post_product_expander.py` | #3, #10, #14 |
| `core/internal_linker.py` | #5 |
| `core/blogger_publisher.py` | #6 |
| `.github/workflows/daily_maintenance.yml` | #7 |
| `core/content_reviewer.py` | #8 |
| `core/sheets_manager.py` | #12 |
| `config/logger.py` | #13 |
| `config/settings.py` | #18 |
| `core/scraper.py` | #17 |
| `core/pipeline.py` (new) | #4, #16 |
| `tests/` (new dir) | #11 |

---

## ROLLBACK STRATEGY

Each fix is independent. If any change breaks existing behavior:
1. Revert the specific file
2. The workflow runs are idempotent (dry-run first, then --apply)
3. Google Sheets execution logs provide audit trail