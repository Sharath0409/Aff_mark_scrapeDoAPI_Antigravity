# Fix Product Placement in First 4 Expanded Posts

## Problem
The Posts Update workflow (`scripts/expand_old_posts.py`) expands old posts from 3 to 5 products. The first 4 posts processed had their new products (4 & 5) inserted **after the FAQ section** instead of **after Product 3** in the product review section.

## Solution
Create a one-time migration script that:
1. Finds the 4 posts with "Expanded to 5" label (oldest first)
2. For each post:
   - Fetches full HTML content
   - Identifies product sections that appear AFTER the FAQ/conclusion
   - Removes those misplaced product sections
   - Reinserts them AFTER the 3rd product section (maintaining order: Product 4 then Product 5)
   - Updates the Blogger post in place
3. Does NOT regenerate any content, images, FAQs, or labels

## Files to Modify

### 1. Create new migration script: `scripts/fix_product_placement.py`
- Standalone script with `--dry-run` and `--apply` modes
- Uses existing `BloggerPublisher`, `SheetsManager`, `ContentGenerator`
- Reuses `_inject_product_sections` logic but in reverse (move existing elements)

### 2. Minor update to `core/post_product_expander.py`
- Add helper function to extract and move existing product sections
- No changes to daily workflow logic

## Implementation Plan

### Step 1: Create Migration Script
```python
# scripts/fix_product_placement.py
# - Finds 4 oldest posts with "Expanded to 5" label
# - For each: fetch, identify misplaced products, move them, update
```

### Step 2: Add Helper Function to post_product_expander.py
```python
def _fix_product_placement(html_content: str) -> str:
    """Move product sections from after FAQ to after 3rd product section."""
    # 1. Find FAQ/conclusion heading
    # 2. Find all product sections after it
    # 3. Remove them
    # 4. Find 3rd product section
    # 5. Insert removed sections after it (maintaining order)
```

### Step 3: Test with dry-run
### Step 4: Apply with --apply

## Safety Requirements
- Dry-run mode by default (no Blogger updates)
- Preserve exact HTML of moved product sections
- Don't regenerate anything
- Handle edge cases (no FAQ, fewer than 3 products, etc.)
- Log all actions for verification

## Regression Analysis
- Only affects 4 specific posts
- No changes to publishing pipeline
- No changes to AI generation
- No changes to image handling
- No schema/FAQ/comparison table modifications