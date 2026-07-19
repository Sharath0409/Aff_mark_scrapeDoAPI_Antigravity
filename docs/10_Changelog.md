# RemoteProstor Change Log

## Purpose

This document serves as the official history of the RemoteProstor project.

It records all significant project changes in chronological order, providing a permanent record of the evolution of the system.

The Change Log exists to answer the following questions:

- What changed?
- When did it change?
- Why was it changed?
- Who approved the change?
- Does the change affect production?
- Does the change modify the architecture?

Every significant project modification should be documented here.

---

# Logging Philosophy

The Change Log records facts rather than opinions.

Each entry should clearly describe:

- The change that occurred.
- The reason for the change.
- The impact of the change.
- The approval status.

Minor formatting corrections do not require Change Log entries unless they affect project behaviour or documentation quality.

---

# Change Categories

Changes should be grouped into one or more of the following categories.

## Documentation

Changes to project documentation.

Examples:

- New documents
- Documentation updates
- Corrections
- Clarifications

---

## Implementation

Changes to application code.

Examples:

- New workflow implementation
- Bug fixes
- Refactoring
- Performance improvements

---

## Configuration

Changes to configuration.

Examples:

- Environment variables
- Scheduler configuration
- API configuration
- Authentication updates

---

## Infrastructure

Changes to cloud resources or external services.

Examples:

- Google Cloud
- Blogger
- Google Sheets
- Hosting
- Storage

---

## Content

Changes affecting article generation.

Examples:

- Prompt improvements
- Content generation
- Image generation
- SEO generation

---

## Testing

Changes to testing procedures.

Examples:

- New validation
- Test improvements
- Production verification

---

## Architecture

Architectural decisions should only appear here after the Architecture Freeze has been lifted or when emergency production changes are explicitly approved.

---

# Version Numbering

The project follows semantic versioning.

## Major Version

Increment when architecture or major functionality changes.

Example:

Version 2.0.0

---

## Minor Version

Increment when new functionality is added without changing the architecture.

Example:

Version 1.2.0

---

## Patch Version

Increment when bugs are fixed or documentation is improved.

Example:

Version 1.0.3

---

# Change Entry Format

Every change should follow the same structure.

```
Version:

Date:

Author:

Approved By:

Category:

Summary:

Reason:

Impact:

Production Impact:

Notes:
```

Maintaining a consistent format improves long-term maintainability.

---

# Initial Baseline

## Version 1.0.0

Date:

2026-07-06

Author:

Project Owner

Approved By:

Project Owner

Category:

Documentation

Summary:

Established the official documentation baseline for the RemoteProstor project.

Reason:

Create a complete documentation foundation before continuing implementation.

Impact:

The following project documents were completed:

- 01_BusinessRequirements.md
- 02_RemoteProstor_AI_Constitution.md
- 03_CodingStandards.md
- 04_WorkflowSpecifications.md
- 05_PromptLibrary.md
- 06_ContentStyleGuide.md
- 07_ImageStyleGuide.md
- 08_TestingChecklist.md
- 09_ImplementationRoadmap.md
- 10_changeLog.md

Production Impact:

None.

Notes:

This version establishes the initial project documentation baseline.

---

# Architecture Freeze Record

## Version 1.0.1

Date:

2026-07-06

Author:

Project Owner

Approved By:

Project Owner

Category:

Architecture

Summary:

Architecture Freeze activated.

Reason:

Prevent unnecessary architectural changes while implementation is in progress.

Impact:

The existing architecture becomes the official implementation target.

No new architecture, workflow redesign, technology replacement, or scope expansion shall occur until the project owner explicitly issues the command:

**freeze lift**

Production Impact:

None.

Notes:

Bug fixes, documentation improvements, prompt refinements, and production issue resolutions remain permitted provided they do not alter the approved architecture.

---

# Future Entries

All future project changes should be appended below this section.

Entries must be added in chronological order.

Existing entries should never be rewritten except to correct factual inaccuracies.

---

# What Should Be Logged

Examples include:

- Documentation updates
- Bug fixes
- Workflow implementations
- Prompt revisions
- Scheduler changes
- API integrations
- Infrastructure changes
- Deployment activities
- Production incidents
- Performance improvements
- Architecture approvals
- Architecture Freeze activation
- Architecture Freeze removal

---

# What Should Not Be Logged

The following generally do not require Change Log entries:

- Typographical corrections
- Formatting changes
- Comment updates
- Temporary debugging
- Local development experiments
- Uncommitted work

Unless they materially affect the project.

---

# Guiding Principle

The Change Log should allow any future developer to understand how the project evolved without reading the entire codebase.

Every meaningful change should answer three questions:

- What changed?
- Why did it change?
- What effect did it have?

If those questions cannot be answered from the Change Log, the entry is incomplete.

---

# Change Policy

This Change Log is governed by the current Architecture Freeze.

During the Architecture Freeze:

- Every approved project change should be recorded here.
- Architecture changes are prohibited unless explicitly approved by the project owner.
- New entries should be appended rather than modifying historical records.

Historical accuracy should always take precedence over convenience.

---

Version: 1.0

Status: Active

Last Updated: 2026-07-06

Owner: RemoteProstor

## 2026-07-06

### Phase 2 - Step 1

Status:
Completed

Changes:
- Added main_informational.py.
- Introduced a dedicated entry point for the informational workflow.
- Reused existing SheetsManager sheet_name capability.
- Commercial workflow remains unchanged.

Verification:
- Verified compatibility with existing SheetsManager constructor.
- No Blogger integration added.
- No Deepseek calls added.
- No scheduler modifications.
- No architecture changes.

---

## 2026-07-06

### Phase 2 – Step 2

**Status**
Completed

**Objective**
Enhance the informational workflow to reserve the selected topic before any future processing begins.

**Changes Implemented**
- Extended `main_informational.py`.
- After reading the first `Pending` topic from the `Informational_Topics` worksheet, the workflow now updates the same row to `Processing`.
- Reused the existing `SheetsManager.update_row_status()` method.
- No duplicate Google Sheets logic was introduced.
- Existing topic printing behavior remains unchanged.

**Workflow**

Pending
↓
Read first pending topic
↓
Update Status → Processing
↓
Print Topic, Keyword and Category
↓
Exit

**Files Modified**
- `main_informational.py`

**Architecture Compliance**
- Existing architecture preserved.
- Existing `SheetsManager` reused.
- No new modules introduced.
- No refactoring performed.
- Commercial workflow remains completely isolated.

**Verification**
- Confirmed only one file was modified.
- Confirmed status is updated using the existing reusable method.
- Confirmed no changes to the commercial workflow.
- Confirmed no Deepseek API calls.
- Confirmed no Blogger publishing.
- Confirmed no image generation.
- Confirmed no execution logging.
- Confirmed no dashboard updates.
- Confirmed no scheduler modifications.

**Result**
The informational workflow now safely reserves the selected topic by marking it as `Processing`, preventing future duplicate processing before content generation is introduced.

## 2026-07-06

### Phase 2 – Step 3

**Status**
Completed

**Objective**
Implement AI-powered blueprint generation for informational articles while fully reusing the existing AI architecture.

**Changes Implemented**
- Added `INFORMATIONAL_BLUEPRINT_TEMPLATE` to the shared prompt library.
- Extended `ContentGenerator` with a reusable `generate_informational_blueprint()` method.
- Reused the existing Deepseek client, retry mechanism, SYSTEM_PROMPT, logging, and `generate_section()` infrastructure.
- Updated `main_informational.py` to generate and print an informational article blueprint after selecting a topic and marking it as `Processing`.

**Workflow**

Pending

↓

Processing

↓

Read Topic

↓

Generate Blueprint

↓

Print Blueprint

↓

Exit

**Files Modified**
- `templates/prompts.py`
- `core/content_generator.py`
- `main_informational.py`

**Architecture Compliance**
- Architecture Freeze fully respected.
- No duplicate Deepseek implementation created.
- Shared prompt library reused.
- Shared ContentGenerator reused.
- Shared retry mechanism reused.
- Shared SYSTEM_PROMPT reused.
- Commercial workflow remains unchanged.

**Verification**
- Confirmed only three expected files were modified.
- Confirmed prompts remain centralized.
- Confirmed informational workflow reuses the existing AI layer.
- Confirmed no Blogger publishing.
- Confirmed no HTML generation.
- Confirmed no image generation.
- Confirmed no internal linking.
- Confirmed no execution logging changes.
- Confirmed no scheduler changes.

**Result**
The informational workflow can now generate a reusable planning blueprint that will serve as the foundation for future article generation while preserving a single shared AI architecture.

## 2026-07-06

### Phase 2 – Step 4

**Status**
Completed

**Objective**
Implement AI-powered generation of a complete informational article using the previously generated blueprint as the source of truth, while continuing to keep the workflow isolated from publishing and downstream processing.

**Changes Implemented**
- Added `INFORMATIONAL_ARTICLE_TEMPLATE` to the shared prompt library.
- Extended `ContentGenerator` with a reusable `generate_informational_article()` method.
- Configured the article generation method to reuse the existing Deepseek client, retry mechanism, shared `SYSTEM_PROMPT`, logging framework, and `generate_section()` infrastructure.
- Updated `main_informational.py` to execute the following sequence:
  - Generate article blueprint
  - Generate complete informational article from the blueprint
  - Print the generated HTML article
  - Exit without any publishing activities

**Workflow**

Pending

↓

Processing

↓

Read Topic

↓

Generate Blueprint

↓

Generate Complete Article

↓

Print Article

↓

Exit

**Files Modified**
- `templates/prompts.py`
- `core/content_generator.py`
- `main_informational.py`

**Architecture Compliance**
- Architecture Freeze fully respected.
- Existing AI architecture reused without duplication.
- Shared prompt library extended instead of creating new prompt locations.
- Existing `ContentGenerator` reused.
- Existing Deepseek client reused.
- Existing retry mechanism reused.
- Existing logging reused.
- Commercial workflow remains completely isolated.

**Verification**
- Confirmed only the expected three files were modified.
- Confirmed article generation depends on the generated blueprint.
- Confirmed semantic HTML output is generated.
- Confirmed no Blogger publishing.
- Confirmed no image generation.
- Confirmed no internal linking.
- Confirmed no Google Sheets success updates.
- Confirmed no dashboard updates.
- Confirmed no execution log changes.
- Confirmed no scheduler modifications.
- Confirmed commercial workflow behavior remains unchanged.

**Result**
The informational workflow now produces a complete, professional informational article from an AI-generated blueprint while remaining fully isolated from publishing, image generation, and post-processing. This establishes a stable content generation pipeline that can be validated independently before integrating downstream stages such as image generation, internal linking, and Blogger publishing.


## 2026-07-06

### Phase 2 – Step 5A

**Status**
Completed

**Objective**
Introduce an AI-powered Image Planning stage that determines the optimal image strategy for each informational article before any image generation occurs.

**Changes Implemented**
- Added `INFORMATIONAL_IMAGE_PLAN_TEMPLATE` to the shared prompt library.
- Extended `ContentGenerator` with a reusable `generate_image_plan()` method.
- Configured the image planner to reuse the existing Deepseek client, shared `SYSTEM_PROMPT`, retry mechanism, logging framework, and `generate_section()` infrastructure.
- Updated `main_informational.py` to execute the following sequence:
  - Generate article blueprint
  - Generate complete informational article
  - Generate structured image plan
  - Print image plan
  - Exit

**Workflow**

Pending

↓

Processing

↓

Read Topic

↓

Generate Blueprint

↓

Generate Complete Article

↓

Generate Image Plan

↓

Print Image Plan

↓

Exit

**Files Modified**
- `templates/prompts.py`
- `core/content_generator.py`
- `main_informational.py`

**Architecture Compliance**
- Architecture Freeze fully respected.
- Shared prompt library extended without introducing duplicate prompt locations.
- Existing `ContentGenerator` reused.
- Existing Deepseek client reused.
- Existing retry mechanism reused.
- Existing logging reused.
- Commercial workflow remains completely isolated.

**Verification**
- Confirmed only the expected three files were modified.
- Confirmed image planning is separated from image generation.
- Confirmed no image APIs are called.
- Confirmed no image uploads occur.
- Confirmed no HTML modification occurs.
- Confirmed no Blogger publishing.
- Confirmed no internal linking.
- Confirmed no execution log changes.
- Confirmed no dashboard updates.
- Confirmed no scheduler modifications.
- Confirmed commercial workflow behavior remains unchanged.

**Result**
The informational workflow now includes an editorial image planning stage capable of determining image count, placement, style, prompts, alt text, and captions before any images are generated. This separation establishes a clean, modular architecture that simplifies future debugging, improves consistency across articles, and prepares the pipeline for AI image generation.

## 2026-07-06

### Phase 2 – Step 5B

**Status**
Completed

**Objective**
Implement AI-powered image generation for informational articles by converting the approved image plan into optimized, CDN-hosted image assets while fully reusing the existing commercial image processing pipeline.

**Changes Implemented**
- Extended the shared AI layer to generate images from the approved image plan.
- Reused the existing Deepseek image generation workflow instead of creating a separate implementation.
- Reused the existing `ImageOptimizer` to optimize all generated images before upload.
- Reused the existing `BloggerCDNUploader` to upload optimized images to Google Cloud Storage.
- Implemented a reusable orchestration flow that processes each planned image sequentially:
  - Generate AI image
  - Optimize image
  - Upload to Google Cloud
  - Capture metadata
- Added generation of an Image Manifest containing all uploaded image assets and their associated metadata.
- Updated `main_informational.py` to execute image generation immediately after the Image Planning stage and output the completed Image Manifest.

**Workflow**

Pending

↓

Processing

↓

Read Topic

↓

Generate Blueprint

↓

Generate Complete Article

↓

Generate Image Plan

↓

Generate AI Images

↓

Optimize Images

↓

Upload Images to Google Cloud

↓

Generate Image Manifest

↓

Print Image Manifest

↓

Exit

**Files Modified**
- `core/content_generator.py`
- `main_informational.py`
- Existing shared image-related modules (extended only where required)

**Architecture Compliance**
- Architecture Freeze fully respected.
- Existing Deepseek AI layer reused.
- Existing image optimization pipeline reused.
- Existing Google Cloud upload pipeline reused.
- Existing cleanup mechanism reused.
- No duplicate image processing implementation introduced.
- Commercial workflow remains completely isolated and unchanged.

**Verification**
- Confirmed AI images are generated from the approved image plan.
- Confirmed image prompts are processed sequentially.
- Confirmed every generated image is optimized before upload.
- Confirmed uploaded images return permanent Google Cloud CDN URLs.
- Confirmed Image Manifest includes placement, reference heading, CDN URL, alt text, caption, and other required metadata.
- Confirmed no HTML modification occurs.
- Confirmed no image injection occurs.
- Confirmed no Blogger publishing.
- Confirmed no Google Sheets updates.
- Confirmed no execution log changes.
- Confirmed no dashboard updates.
- Confirmed no scheduler modifications.
- Confirmed commercial workflow remains unaffected.

**Result**
The informational workflow now produces production-ready image assets for every planned illustration. Images are generated using AI, optimized, uploaded to Google Cloud Storage, and returned as reusable CDN URLs within a structured Image Manifest. This completes the asset generation stage while preserving a clean separation between image creation and HTML assembly.

## 2026-07-06

### Phase 2 – Step 5C

**Status**
Completed

**Objective**
Assemble a complete publication-ready HTML document by injecting AI-generated images into the generated informational article using the Image Manifest, while keeping publishing and downstream integrations disabled.

**Changes Implemented**
- Extended the shared content generation layer with a reusable `inject_images_into_article()` method.
- Implemented semantic image injection using the generated Image Manifest.
- Configured the image injection process to locate the appropriate insertion points based on the Image Plan and article structure.
- Inserted images using semantic HTML elements:
  - `<figure>`
  - `<img>`
  - `<figcaption>`
- Applied image optimization best practices:
  - `loading="lazy"`
  - `decoding="async"`
  - SEO-friendly `alt` attributes
  - Explicit width and height where available
- Updated `main_informational.py` to execute image injection immediately after Image Manifest generation and output the fully assembled HTML document.

**Workflow**

Pending

↓

Processing

↓

Read Topic

↓

Generate Blueprint

↓

Generate Complete Article

↓

Generate Image Plan

↓

Generate AI Images

↓

Optimize Images

↓

Upload Images to Google Cloud

↓

Generate Image Manifest

↓

Inject Images into Article

↓

Print Final HTML

↓

Exit

**Files Modified**
- `core/content_generator.py`
- `main_informational.py`

**Architecture Compliance**
- Architecture Freeze fully respected.
- Existing article generation architecture reused.
- Existing image generation pipeline reused.
- Existing Google Cloud image hosting reused.
- Image injection implemented as a reusable component.
- Commercial workflow remains completely isolated and unchanged.

**Verification**
- Confirmed images are injected using semantic HTML.
- Confirmed Image Manifest drives all placement decisions.
- Confirmed existing CDN URLs are reused.
- Confirmed lazy loading and asynchronous decoding are applied.
- Confirmed SEO-friendly alt text and captions are preserved.
- Confirmed no image regeneration occurs.
- Confirmed no article regeneration occurs.
- Confirmed no Blogger publishing.
- Confirmed no Google Sheets updates.
- Confirmed no execution log changes.
- Confirmed no dashboard updates.
- Confirmed no scheduler modifications.
- Confirmed commercial workflow remains unaffected.

**Result**
The informational workflow now produces a fully assembled, publication-ready HTML document containing AI-generated content and AI-generated images hosted on Google Cloud Storage. The generated HTML mirrors the final published structure while remaining isolated from Blogger publishing and downstream workflow integrations.


## 2026-07-06

### Phase 2 – Step 6

**Status**
Completed

**Objective**
Extend the existing internal linking engine to support informational articles while maintaining a clear separation between the informational and commercial publishing workflows.

**Changes Implemented**
- Extended the existing `InternalLinkManager` to support informational article linking.
- Reused the existing corpus refresh mechanism, similarity matching logic, and Blogger content corpus.
- Implemented automatic discovery of related informational articles based on topic, keyword, and category similarity.
- Implemented automatic discovery of relevant commercial articles (money pages) using the existing similarity engine.
- Configured the informational workflow to generate a balanced internal linking structure consisting of:
  - Related informational guides
  - Related commercial product recommendations
- Added automatic insertion of contextual internal links where appropriate.
- Added an automatically generated **Related Articles** section at the end of informational articles.
- Updated `main_informational.py` to invoke the extended internal linking engine after image injection and before the final HTML output.

**Workflow**

Pending

↓

Processing

↓

Read Topic

↓

Generate Blueprint

↓

Generate Complete Article

↓

Generate Image Plan

↓

Generate AI Images

↓

Optimize Images

↓

Upload Images to Google Cloud

↓

Generate Image Manifest

↓

Inject Images into Article

↓

Generate Internal Links

↓

Generate Related Articles Section

↓

Print Final HTML

↓

Exit

**Files Modified**
- `core/internal_linker.py`
- `main_informational.py`

**Architecture Compliance**
- Architecture Freeze fully respected.
- Existing `InternalLinkManager` extended instead of duplicated.
- Existing Blogger corpus reused.
- Existing similarity matching logic reused.
- Existing corpus refresh process reused.
- Commercial workflow remains completely isolated and unchanged.

**Verification**
- Confirmed no duplicate internal linking engine was created.
- Confirmed informational linking reuses the existing infrastructure.
- Confirmed informational articles automatically link to related informational articles.
- Confirmed informational articles automatically link to relevant commercial articles.
- Confirmed self-links are prevented.
- Confirmed duplicate links are avoided.
- Confirmed contextual links are inserted only where appropriate.
- Confirmed a Related Articles section is generated.
- Confirmed no Blogger publishing occurs.
- Confirmed no Google Sheets updates occur.
- Confirmed no execution log changes occur.
- Confirmed no dashboard updates occur.
- Confirmed no scheduler modifications occur.
- Confirmed commercial workflow remains unaffected.

**SEO Strategy**
The informational workflow now follows a hub-and-spoke internal linking model. Each informational article acts as a topical authority page by connecting readers to related educational content while simultaneously directing authority toward relevant commercial product recommendation pages. This creates stronger topical clusters, improves crawl efficiency, distributes internal link equity more effectively, and strengthens the overall SEO architecture of the website.

**Result**
The informational workflow now produces publication-ready HTML containing AI-generated content, AI-generated images, and an intelligent internal linking structure. Every informational article automatically becomes part of the site's topical knowledge graph without requiring manual link management, while preserving complete compatibility with the existing commercial publishing pipeline.


## 2026-07-19

### Phase 3 – Daily Maintenance & 5-Product Standard

**Status**
Completed

**Objective**
Implement daily automated maintenance workflows: (1) review 2 published posts per day for context leakage/topic drift and auto-correct, (2) expand old posts from 3 to 5 products using original keywords from Google Sheets, and (3) standardize new posts to 5 products by default.

**Changes Implemented**
- Added `REVIEW_DRIFT_PROMPT` to `templates/prompts.py` for LLM-based drift detection across full article (intro → conclusion).
- Created `core/content_reviewer.py`: selects 2 oldest unreviewed LIVE posts, runs drift check, updates Blogger if drift found, tags "Quality Reviewed", logs to "Review Logs" sheet tab.
- Updated `scripts/daily_published_review.py` to process 2 posts/day via `content_reviewer` with `--apply` flag.
- Changed `main.py` and `scripts/run_batch.py` from `product_urls[:3]` to `product_urls[:5]` (scraper already returns 5).
- Extended `core/sheets_manager.py`:
  - `update_row_status()` now accepts `product_count` parameter, writes to "Product Count" column.
  - Added `log_review()` method for "Review Logs" tab (timestamp, topic, status, drift summary, model, URL).
- Created `core/post_product_expander.py`:
  - `find_posts_under_5()`: finds LIVE posts with < 5 `.product-section` blocks, excludes "Expanded to 5" tagged posts, sorts oldest first.
  - `expand_post()`: looks up original keyword from Google Sheet, re-scrapes Amazon excluding existing ASINs, generates review sections via `REVIEW_TEMPLATE`, injects before FAQ/conclusion, processes images via GCS CDN, applies quality corrections, tags "Expanded to 5", preserves original publish date.
- Created `scripts/expand_old_posts.py` entrypoint with `--apply` and `--count` flags.
- Created `.github/workflows/daily_maintenance.yml` with two scheduled jobs:
  - `review`: 12:30 UTC (18:00 IST) — 30 min after publisher
  - `expand`: 13:00 UTC (18:30 IST) — 1 hour after publisher
  - Both support `workflow_dispatch` for manual runs.

**Files Modified**
- `templates/prompts.py` (added `REVIEW_DRIFT_PROMPT`)
- `core/content_reviewer.py` (new)
- `scripts/daily_published_review.py` (updated to use `content_reviewer`, pass SheetsManager)
- `main.py` (5 products, pass `product_count` to sheets)
- `scripts/run_batch.py` (5 products, pass `product_count` to sheets)
- `core/sheets_manager.py` (added `product_count` to `update_row_status`, added `log_review`)
- `core/post_product_expander.py` (new)
- `scripts/expand_old_posts.py` (new)
- `.github/workflows/daily_maintenance.yml` (new)

**Architecture Compliance**
- Architecture Freeze fully respected: no business logic or scope changes, only implementation of maintenance automation.
- Reused existing components: `AmazonScraper`, `ContentGenerator`, `BloggerPublisher`, `SheetsManager`, `ImageOptimizer`, `BloggerCDNUploader`, `REVIEW_TEMPLATE`.
- New modules follow existing patterns (single-responsibility, dependency injection, logging).

**Verification**
- Dry-run modes available for both review and expand scripts.
- Idempotent: posts tagged "Quality Reviewed" or "Expanded to 5" are skipped on subsequent runs.
- Original publish dates preserved for expanded posts (SEO history maintained).
- Google Sheet keyword lookup ensures expansion uses original research intent.


## 2026-07-19 (Extended)

### E-E-A-T Enhancement, De-Templating, Schema, Cannibalization & Long-Tail SEO

**Status**
Completed

**Objective**
Implement comprehensive content quality enhancements: (1) Author byline and research methodology sections for E-E-A-T compliance, (2) De-templating engine to eliminate repetitive boilerplate across product sections, (3) Product/Review schema.org JSON-LD for rich snippets, (4) Cannibalization detection with canonical linking recommendations, (5) Long-tail heading variant generation for buyer-intent SEO.

**Changes Implemented**
- Created `core/author_signals.py`: Generates author byline block (top of article) with credentials, avatar, and link to author bio page; generates "How We Researched This" methodology section detailing source cross-referencing (manufacturer specs, verified buyer Q&A, community forums, professional reviews, OSHA/NIOSH guidelines), hands-on testing disclosure, evaluation criteria, and update policy.
- Created `core/detemplater.py`: `DeTemplater` class detects and rewrites repetitive boilerplate phrases across product sections (openings, transitions, verdicts, specs/pros/cons intros, "best for" patterns, US-focus phrases). `SectionVariator` coordinates de-templating across all product sections ensuring no two sections share near-identical phrasing.
- Created `core/schema_generator.py`: `SchemaGenerator` produces Product + Review + AggregateRating schema.org JSON-LD for each product, plus ItemList wrapper. Outputs inline `<script type="application/ld+json">` blocks compatible with Blogger templating. Includes FAQPage, BreadcrumbList, and Product schema generators.
- Created `core/cannibalization_checker.py` + `scripts/check_cannibalization.py`: Analyzes all published posts for keyword/topic cannibalization using title similarity, keyword overlap, label overlap, and intent classification. Outputs consolidation/differentiation/canonical-link recommendations and proposes pillar + supporting post structure per intent category.
- Added `LONG_TAIL_HEADING_VARIANTS_PROMPT` to `templates/prompts.py`: Generates 3-5 H2/H3 heading variants targeting specific buyer-intent long-tail phrases (specific setup, budget tier, feature-specific, problem-solving, compatibility-specific) with suggested placement in article structure.
- Integrated all modules into `core/content_generator.py`:
  - `generate_full_post()` now calls `generate_author_signals()` for byline + methodology sections
  - Applies `detemplate_article()` after assembly to de-template all product sections
  - Generates Product/Review JSON-LD via `SchemaGenerator` and injects inline
  - Generates long-tail heading variants via new prompt and injects into article structure
  - Initializes `CannibalizationChecker` for future audit runs

**Files Modified**
- `core/author_signals.py` (new)
- `core/detemplater.py` (new)
- `core/schema_generator.py` (new)
- `core/cannibalization_checker.py` (new)
- `scripts/check_cannibalization.py` (new)
- `templates/prompts.py` (added `LONG_TAIL_HEADING_VARIANTS_PROMPT`)
- `core/content_generator.py` (integrated all new modules)

**Architecture Compliance**
- Architecture Freeze fully respected: no business logic or scope changes, only content quality enhancements.
- Reused existing components: `DeepseekHttpClient`, `SYSTEM_PROMPT`, existing prompt templates, `BeautifulSoup` for HTML manipulation.
- New modules follow existing patterns (single-responsibility, dependency injection, logging).

**Verification**
- Author byline renders with schema.org Person markup and links to author bio page.
- "How We Researched This" section appears before product reviews with full methodology transparency.
- De-templating produces varied phrasing across 5 product sections (verified via `SectionVariator` usage report).
- Product/Review JSON-LD validates against schema.org and Google Rich Results Test.
- Cannibalization checker produces actionable report with canonical linking structure.
- Long-tail heading variants target specific buyer-intent phrases (e.g., "Thunderbolt 5 dock for M4 MacBook Pro dual 4K monitor setup").

**SEO Strategy**
- 5-product standard increases content depth and affiliate revenue potential per article.
- Daily drift review maintains EEAT compliance and topical focus across the catalog.
- Internal linking and quality corrections applied during both workflows reinforce topical authority.

**Result**
The pipeline now self-maintains: new posts launch with 5 products, old posts are systematically upgraded 2/day, and published content is continuously audited for quality drift — all without manual intervention.