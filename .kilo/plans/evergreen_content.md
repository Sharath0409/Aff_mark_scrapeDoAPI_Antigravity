# Plan: Remove Year-Based Wording for Evergreen Content

## Objective
Ensure all generated content is evergreen by removing marketing-style years (2024, 2025, 2026, etc.) while preserving factual years.

## Implementation Strategy

### 1. SYSTEM_PROMPT Update (templates/prompts.py)
Add explicit evergreen instruction to the global system prompt that applies to ALL content generation.

### 2. Content Generator Validation (core/content_generator.py)
Add year detection and removal in `_apply_quality_corrections()` method that runs on ALL generated content before returning.

### 3. Template-Level Reinforcement
Add evergreen reminders to key templates:
- SEO_TAGS_TEMPLATE (already has "Do NOT include dates or years")
- INTRO_TEMPLATE
- REVIEW_TEMPLATE
- QUICK_SUMMARY_TEMPLATE
- CONCLUSION_TEMPLATE
- FAQ_TEMPLATE
- COMPARISON_TEMPLATE

### 4. Year Detection Logic
- Pattern: `\b(20\d{2})\b` - matches 2000-2099
- Preserve factual years (OSHA updates, product releases, version numbers like Windows 11 24H2)
- Remove marketing years ("Best of 2024", "2025 Guide", "for 2024", "in 2025")

### 5. Validation Coverage
- Title / SEO Title
- Meta Title
- Meta Description
- Headings (H1, H2, H3)
- Body content
- FAQs
- Conclusion
- SEO Labels
- Image Prompts
- Image Alt Text
- Internal Link Anchor Text

## Files to Modify
1. `templates/prompts.py` - SYSTEM_PROMPT + template reinforcements
2. `core/content_generator.py` - Add year validation in `_apply_quality_corrections()`

## Testing
- Run unit tests to ensure no regressions
- Verify year removal works for marketing years but preserves factual years