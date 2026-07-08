# RemoteProstor Workflow Specifications

## Purpose

This document defines the operational workflows of the RemoteProstor publishing system.

It serves as the functional reference for how each workflow should execute from start to finish.

These workflows describe the expected system behavior and should be followed consistently throughout development and production.

This document defines workflow behavior only. It does not define implementation details or programming logic.

---

# Workflow Overview

The RemoteProstor publishing system consists of two publishing workflows.

1. Commercial Publishing Workflow
2. Informational Publishing Workflow

Both workflows share common infrastructure wherever possible while following different content generation strategies.

The workflows ultimately publish content to the same Blogger website and maintain a unified execution history.

---

# Commercial Publishing Workflow

## Purpose

Generate and publish affiliate-focused product recommendation articles using Amazon product information.

---

## Workflow Sequence

### Step 1 — Scheduler Execution

The workflow begins when the scheduler triggers the publishing pipeline.

Only one article should be processed during each execution.

---

### Step 2 — Read Pending Topic

The system reads the next topic marked as **Pending** from the **Sheet1** worksheet.

The selected row becomes the active publishing task.

---

### Step 3 — Pending Topic Validation

Before processing begins, the workflow verifies:

- Topic exists
- Keyword exists
- Status is Pending

If validation fails, the workflow terminates safely.

---

### Step 4 — Duplicate Detection

The system compares the topic against:

- Previously published Blogger posts
- Previously processed Google Sheet entries

Duplicate topics are skipped.

The worksheet is updated accordingly.

---

### Step 5 — Amazon Product Search

The system searches Amazon using the configured keyword.

Multiple retry attempts may be performed if no products are initially found.

If no products are available after all retry attempts, the workflow terminates as Failed.

---

### Step 6 — Product Data Collection

Product information is collected for the selected products.

Typical information includes:

- Product title
- Price
- Rating
- Review count
- Features
- Product image
- Product URL

---

### Step 7 — Image Processing

Downloaded product images are:

- Optimized
- Converted if required
- Uploaded to the configured Google Cloud Storage bucket

The uploaded image URL becomes the permanent image used within the article.

---

### Step 8 — Content Generation

The article is generated using the commercial content generation pipeline.

The generated article includes:

- Introduction
- Quick summary
- Product reviews
- Comparison section
- Frequently asked questions
- Conclusion
- Affiliate disclosure

---

### Step 9 — SEO Label Generation

SEO labels are generated for Blogger.

The article category is added if not already present.

---

### Step 10 — Internal Linking

Relevant published articles are identified.

Contextual internal links are inserted into the generated article.

A related articles section is added where appropriate.

---

### Step 11 — HTML Cleanup

The generated HTML is cleaned before publication.

Required formatting adjustments are applied to ensure Blogger compatibility.

---

### Step 12 — Blogger Publishing

The article is published to Blogger.

The workflow captures:

- Published URL
- Blogger Post ID

---

### Step 13 — Google Sheets Update

The worksheet is updated with:

- Status
- Publish Date
- Blog URL
- Post ID

---

### Step 14 — Dashboard Update

Dashboard statistics are refreshed to reflect the completed execution.

---

### Step 15 — Execution Logging

The workflow records execution details within the Execution Logs worksheet.

---

### Step 16 — Notification

A completion notification is generated indicating either:

- Success
- Failure
- Warning

The workflow then terminates.

---

# Informational Publishing Workflow

## Purpose

Generate educational, high-quality informational articles that strengthen topical authority and improve internal content coverage.

---

## Workflow Sequence

### Step 1 — Scheduler Execution

The workflow begins when the scheduler triggers the publishing pipeline.

Only one informational article should be processed during each execution.

---

### Step 2 — Read Pending Topic

The system reads the next topic marked as **Pending** from the **Informational_Topics** worksheet.

---

### Step 3 — Pending Topic Validation

The workflow validates:

- Topic
- Keyword
- Status

Invalid rows are skipped.

---

### Step 4 — Duplicate Detection

Duplicate detection follows the same rules used by the commercial workflow.

Previously published or processed topics are skipped.

---

### Step 5 — Content Generation

The informational content generator creates a complete article.

The article is generated according to the approved content standards.

---

### Step 6 — AI Image Generation

Original images are generated specifically for the article.

Images should support the educational purpose of the content.

Internet images should not be used.

---

### Step 7 — Image Upload

Generated images are uploaded using the existing image upload process.

The resulting URLs are inserted into the article.

---

### Step 8 — SEO Label Generation

SEO labels are generated.

The article category is included if necessary.

---

### Step 9 — Internal Linking

Relevant published articles are identified.

Internal links are added naturally throughout the article.

A related articles section is added where appropriate.

---

### Step 10 — HTML Cleanup

The generated HTML is prepared for Blogger publication.

---

### Step 11 — Blogger Publishing

The completed article is published to Blogger.

The workflow stores:

- Published URL
- Blogger Post ID

---

### Step 12 — Google Sheets Update

The Informational_Topics worksheet is updated.

The execution status is recorded.

---

### Step 13 — Dashboard Update

Dashboard statistics are refreshed.

---

### Step 14 — Execution Logging

Execution details are written to the Execution Logs worksheet.

---

### Step 15 — Notification

Completion notification is generated.

The workflow then terminates.

---

# Scheduler Workflow

## Purpose

The scheduler is responsible for automatically initiating the publishing process.

Only one publishing workflow should execute during each scheduled run.

The scheduler should determine which publishing workflow to execute according to the approved publishing schedule.

The scheduler should not initiate multiple publishing workflows simultaneously.

---

# Google Sheets Workflow

## Purpose

Google Sheets acts as the primary workflow controller.

It maintains:

- Publishing queue
- Workflow status
- Dashboard statistics
- Execution history

Google Sheets remains the authoritative source for workflow state.

---

## Status Lifecycle

Topics move through the following lifecycle.

Pending

↓

Success

or

Failed

or

Skipped

Status changes should always be reflected within the worksheet.

---

# Internal Linking Workflow

## Purpose

Internal links improve navigation and strengthen topical relationships.

The workflow identifies relevant published articles before publication.

Internal links should:

- Be contextually relevant
- Improve reader navigation
- Appear naturally
- Avoid excessive repetition

---

# Blogger Publishing Workflow

## Purpose

Publish completed articles to Blogger.

The publishing workflow should:

- Publish HTML content
- Apply labels
- Capture published URL
- Capture Blogger Post ID
- Return publication status

Only successful publications should update Google Sheets as Success.

---

# Logging Workflow

## Purpose

Every workflow execution should generate meaningful logs.

Logs should include:

- Workflow start
- Workflow completion
- Warnings
- Errors
- Retry attempts
- Published URL
- Execution status

Logs should assist with troubleshooting and production monitoring.

---

# Notification Workflow

## Purpose

Notifications inform the project owner about workflow outcomes.

Notifications should be generated for:

- Successful publication
- Workflow failure
- Important warnings

Notifications should contain sufficient information to identify the completed publishing task.

---

# Failure Handling Workflow

Whenever a recoverable failure occurs, the workflow should attempt recovery according to the implementation.

If recovery is unsuccessful:

- Stop processing safely.
- Preserve useful logs.
- Update Google Sheets.
- Record the failure.
- Generate a notification.

The workflow should never leave the publishing queue in an inconsistent state.

---

# Workflow Completion

A workflow execution is considered complete only after:

- Processing has finished.
- Google Sheets has been updated.
- Dashboard statistics have been updated.
- Execution logs have been recorded.
- Notifications have been generated.

Only then should the workflow terminate.

---

# Change Policy

This document is governed by the current Architecture Freeze.

Workflow definitions described in this document shall not be modified until the project owner explicitly lifts the Architecture Freeze.

Minor wording improvements and documentation corrections are permitted provided they do not change workflow behavior.

---

Version: 1.0

Status: Active

Last Updated: 2026-07-06

Owner: RemoteProstor