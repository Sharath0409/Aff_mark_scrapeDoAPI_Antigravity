# RemoteProstor Prompt Library

## Purpose

This document defines the prompt architecture used throughout the RemoteProstor publishing system.

Prompts are responsible for guiding the AI to generate consistent, accurate, and production-ready output while maintaining the editorial standards of the project.

This document describes the purpose and expected behaviour of each prompt rather than storing the prompt text itself.

Prompt implementations remain within the project source code.

---

# Prompt Design Philosophy

Every prompt should guide the AI toward producing content that is:

- Helpful
- Accurate
- Reader-focused
- Well structured
- Professional
- Easy to understand
- Factually responsible

Prompts should minimize ambiguity and produce consistent output across repeated executions.

---

# General Prompt Standards

Every prompt should:

- Have a clearly defined purpose.
- Request only the required output.
- Avoid conflicting instructions.
- Produce deterministic structure where appropriate.
- Maintain a professional writing style.
- Avoid unnecessary verbosity.
- Follow the RemoteProstor Content Style Guide.

Prompts should never encourage the AI to fabricate information or invent unsupported claims.

---

# System Prompt

## Purpose

Defines the overall behaviour of the AI during content generation.

The System Prompt establishes:

- Writing style
- Professional tone
- Reader-first philosophy
- Content quality expectations
- Formatting expectations

Every content generation request begins with the System Prompt.

---

# Introduction Prompt

## Purpose

Generate the opening section of an article.

The introduction should:

- Explain the problem.
- Establish context.
- Match search intent.
- Encourage continued reading.
- Avoid unnecessary storytelling.

The introduction should transition naturally into the remainder of the article.

---

# Product Review Prompt

## Purpose

Generate detailed product reviews for commercial articles.

Each review should discuss:

- Product overview
- Strengths
- Limitations
- Ideal use cases
- Important features
- Balanced evaluation

Reviews should remain objective and avoid exaggerated marketing language.

---

# Comparison Prompt

## Purpose

Generate comparison content between multiple products.

Comparisons should help readers understand meaningful differences.

The generated comparison should remain unbiased and easy to scan.

---

# Quick Summary Prompt

## Purpose

Generate a concise overview before detailed reviews.

The summary should allow readers to understand the article quickly before reading the complete content.

---

# FAQ Prompt

## Purpose

Generate frequently asked questions related to the article topic.

FAQs should answer realistic questions readers may search for.

Answers should remain concise while providing practical value.

---

# Conclusion Prompt

## Purpose

Generate the closing section of the article.

The conclusion should:

- Summarize key findings.
- Reinforce important recommendations.
- End naturally.
- Avoid repetitive marketing language.

The conclusion should not introduce new information.

---

# SEO Labels Prompt

## Purpose

Generate Blogger labels for published articles.

Labels should:

- Be relevant.
- Be concise.
- Avoid duplication.
- Support content organization.
- Remain within Blogger limitations.

Only meaningful labels should be generated.

---

# Informational Article Prompt

## Purpose

Generate complete educational articles for informational topics.

The generated content should:

- Answer the user's question completely.
- Follow the approved writing standards.
- Prioritize practical guidance.
- Include logical section flow.
- Maintain professional tone.
- Build topical authority.

The prompt should adapt naturally to different informational topics while preserving overall article quality.

---

# AI Image Prompt

## Purpose

Generate original images for informational articles.

Generated images should:

- Support the educational purpose of the article.
- Be visually clean.
- Avoid excessive decorative elements.
- Match the article topic.
- Maintain a professional appearance.

Images should never imitate copyrighted artwork or reproduce images from external sources.

---

# Internal Linking Prompt

## Purpose

Guide the AI in inserting contextual internal links.

Links should:

- Improve navigation.
- Support topical authority.
- Feel natural within the article.
- Never interrupt readability.

Internal links should always benefit the reader.

---

# HTML Formatting Prompt

## Purpose

Ensure generated content follows the required HTML structure before publication.

Formatting should remain:

- Clean
- Consistent
- Accessible
- Compatible with Blogger

Presentation should support readability rather than decoration.

---

# Prompt Maintenance

Prompts should evolve only when they improve one or more of the following:

- Content quality
- Reader experience
- Accuracy
- Consistency
- Stability

Prompt changes should never reduce article quality or introduce inconsistent behaviour.

---

# Prompt Versioning

Whenever a production prompt is modified, the change should be documented.

The documented reason should explain:

- Why the prompt changed.
- What improvement was expected.
- Which workflow uses the prompt.

Prompt updates should remain backward compatible whenever practical.

---

# Prompt Validation

Before a prompt is approved for production, it should be evaluated for:

- Correctness
- Clarity
- Consistency
- Output quality
- Formatting quality
- Hallucination resistance
- Compliance with project standards

Only validated prompts should be used in automated publishing workflows.

---

# Guiding Principle

Every prompt exists for one purpose:

To consistently produce high-quality output that benefits the reader while supporting the long-term goals of RemoteProstor.

Prompt complexity should never be mistaken for prompt quality.

The best prompt is the one that consistently produces reliable production-ready results.

---

# Change Policy

This Prompt Library is governed by the current Architecture Freeze.

No new prompt categories, prompt workflows, or prompt responsibilities shall be introduced until the Architecture Freeze has been officially lifted by the project owner.

Existing prompts may receive wording improvements only when such changes improve output quality without altering the approved workflow.

---

Version: 1.0

Status: Active

Last Updated: 2026-07-06

Owner: RemoteProstor