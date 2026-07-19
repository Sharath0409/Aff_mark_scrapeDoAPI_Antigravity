# RemoteProstor Testing Checklist

## Purpose

This document defines the testing requirements for the RemoteProstor publishing system.

Its objective is to ensure that every workflow, article, image, and integration operates reliably before and after deployment.

Testing should verify system correctness, stability, reliability, and production readiness.

This checklist applies to both Commercial and Informational publishing workflows.

---

# Testing Philosophy

Every production execution should produce predictable and reliable results.

Testing is not performed to prove that the system works once.

Testing is performed to verify that the system continues to work consistently after future updates.

The objective is to detect problems before they affect published content or production workflows.

---

# Pre-Deployment Testing

Before deploying any workflow changes, verify that:

- The project builds successfully.
- Required dependencies are available.
- Configuration values are valid.
- Required API credentials are configured.
- Google services are accessible.
- Blogger authentication succeeds.
- Deepseek authentication succeeds.
- Google Cloud authentication succeeds.

Deployment should not proceed if any required dependency is unavailable.

---

# Google Sheets Testing

Verify that the workflow can:

- Read pending topics.
- Identify the correct worksheet.
- Read all required columns.
- Update workflow status.
- Update publish date.
- Store published URLs.
- Store Blogger Post IDs.
- Record execution logs.
- Update dashboard statistics.

No worksheet should be left in an inconsistent state.

---

# Scheduler Testing

Verify that the scheduler:

- Executes at the expected time.
- Triggers only one publishing workflow.
- Does not execute duplicate jobs.
- Continues normal operation after previous successful runs.

The scheduler should remain reliable over repeated executions.

---

# Commercial Workflow Testing

Verify that the Commercial workflow can:

- Select the correct pending topic.
- Detect duplicate topics.
- Retrieve Amazon products.
- Collect complete product information.
- Download product images.
- Optimize product images.
- Upload images successfully.
- Generate article content.
- Generate SEO labels.
- Insert internal links.
- Publish successfully to Blogger.
- Update Google Sheets.
- Record execution logs.

Every stage should complete successfully before the workflow is considered production ready.

---

# Informational Workflow Testing

Verify that the Informational workflow can:

- Select the correct pending topic.
- Detect duplicate topics.
- Generate complete informational articles.
- Generate AI images.
- Upload generated images.
- Insert internal links.
- Publish successfully.
- Update Google Sheets.
- Record execution logs.

Every generated article should satisfy the Content Style Guide before publication.

---

# AI Content Testing

Every generated article should be reviewed for:

- Correct topic coverage.
- Logical structure.
- Professional writing.
- No factual hallucinations.
- No unnecessary repetition.
- No filler content.
- Proper grammar.
- Natural flow.
- Useful recommendations.
- Appropriate article length.

Generated content should require minimal manual editing before publication.

---

# SEO Testing

Verify that every article:

- Uses the intended title.
- Contains relevant headings.
- Uses appropriate labels.
- Has meaningful internal links.
- Uses descriptive image alt text.
- Targets the intended search intent.

SEO optimization should improve discoverability without reducing readability.

---

# Image Testing

Commercial articles:

Verify that:

- Product images download correctly.
- Images upload successfully.
- Image URLs remain accessible.
- Images display correctly.
- Alt text is present.

Informational articles:

Verify that:

- Images are AI generated.
- Images match the article topic.
- Images improve understanding.
- Images display correctly.
- Image quality remains consistent.

---

# Blogger Testing

Verify that published articles:

- Display correctly.
- Preserve formatting.
- Preserve images.
- Preserve headings.
- Preserve internal links.
- Preserve affiliate links.
- Preserve labels.

The published article should match the generated content.

---

# Internal Linking Testing

Verify that:

- Links point to existing articles.
- Links are contextually relevant.
- Links are not broken.
- Related article sections display correctly.

Internal links should improve navigation without distracting readers.

---

# Logging Testing

Verify that logs correctly record:

- Workflow start.
- Workflow completion.
- Retry attempts.
- Warnings.
- Failures.
- Published URLs.
- Processing duration where available.

Logs should provide sufficient information for troubleshooting.

---

# Error Recovery Testing

Simulate common failure scenarios.

Examples include:

- Google Sheets unavailable.
- Blogger unavailable.
- Amazon unavailable.
- Deepseek unavailable.
- Google Cloud unavailable.
- Invalid credentials.
- Missing configuration.
- Network interruption.

Verify that failures are:

- Logged.
- Reported.
- Safely handled.
- Recorded in Google Sheets.

The workflow should terminate safely without corrupting workflow state.

---

# Duplicate Detection Testing

Verify that duplicate topics are:

- Correctly identified.
- Not published.
- Logged appropriately.
- Updated within Google Sheets.

Duplicate detection should prevent accidental republishing.

---

# Notification Testing

Verify that notifications are generated for:

- Successful publication.
- Failed execution.
- Important warnings.

Notifications should contain sufficient information for troubleshooting.

---

# Performance Testing

Verify that:

- Workflow completes successfully.
- API requests remain within expected limits.
- Images are optimized.
- Generated HTML remains manageable.
- Publishing time remains acceptable.

Performance improvements should never compromise reliability.

---

# Production Readiness Checklist

Before enabling automated publishing, confirm:

✓ Google Sheets integration verified

✓ Blogger publishing verified

✓ Commercial workflow verified

✓ Informational workflow verified

✓ AI image generation verified

✓ Internal linking verified

✓ Dashboard updates verified

✓ Execution logging verified

✓ Notifications verified

✓ Error recovery verified

✓ Scheduler verified

✓ Duplicate detection verified

✓ Article quality verified

✓ Image quality verified

✓ SEO verification completed

Only after every item has been verified should autonomous publishing be enabled.

---

# Post-Deployment Monitoring

After deployment, monitor:

- Daily workflow execution.
- Publishing success rate.
- Execution failures.
- Google Sheets updates.
- Blogger publishing.
- Generated article quality.
- Search indexing progress.
- Internal link integrity.

Any recurring issue should be investigated before additional changes are introduced.

---

# Success Criteria

The RemoteProstor publishing system is considered production ready when:

- Both publishing workflows execute successfully.
- Published articles meet editorial standards.
- Images display correctly.
- Google Sheets remain synchronized.
- Blogger publishing succeeds consistently.
- Logging remains accurate.
- Notifications function correctly.
- No critical production issues are observed.

---

# Guiding Principle

Testing is complete only when there is reasonable confidence that the system can execute reliably without manual intervention while maintaining the expected quality standards.

---

# Change Policy

This Testing Checklist is governed by the current Architecture Freeze.

Testing requirements defined in this document shall remain unchanged until the project owner explicitly lifts the Architecture Freeze.

Minor wording improvements and documentation corrections are permitted provided they do not alter the intent of this checklist.

---

Version: 1.0

Status: Active

Last Updated: 2026-07-06

Owner: RemoteProstor