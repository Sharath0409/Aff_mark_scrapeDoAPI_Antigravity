# RemoteProstor Coding Standards

## Purpose

This document defines the engineering standards that must be followed while developing, maintaining, or extending the RemoteProstor codebase.

Its objective is to ensure that every change remains consistent, maintainable, reliable, and production-ready.

These standards apply to all future development unless explicitly superseded by the project owner after the Architecture Freeze has been lifted.

---

## Engineering Philosophy

The RemoteProstor codebase should prioritize reliability over cleverness.

Code should be easy to understand, easy to maintain, and easy to debug.

Every change should reduce long-term maintenance effort rather than increase it.

A solution that is slightly longer but significantly easier to understand is preferred over a shorter but complex implementation.

---

## General Principles

Every implementation should follow these principles:

- Write code for humans first.
- Optimize for readability.
- Keep solutions simple.
- Avoid unnecessary complexity.
- Prefer explicit behaviour over hidden behaviour.
- Reuse existing modules whenever possible.
- Never duplicate business logic.
- Preserve existing functionality unless a change is explicitly approved.

---

## Code Quality

Every module should be:

- Readable
- Predictable
- Maintainable
- Properly logged
- Properly validated
- Safe to modify

Code should clearly communicate its intent.

Future maintenance should not require guessing what the original developer intended.

---

## Single Responsibility

Every module should have one primary responsibility.

Examples:

- SheetsManager manages Google Sheets.
- ContentGenerator generates content.
- BloggerPublisher publishes content.
- InternalLinkManager manages internal links.
- AmazonScraper retrieves product information.

A module should not perform unrelated responsibilities.

---

## Reuse Before Creating

Before creating a new module or function, determine whether the existing codebase already provides the required functionality.

If an existing implementation satisfies the requirement, it should be reused.

Creating duplicate functionality should always be considered a last resort.

---

## Backward Compatibility

Working functionality should never be broken by new development.

Whenever new features are introduced, existing behaviour should continue to operate exactly as before unless explicitly approved by the project owner.

Regression should always be avoided.

---

## File Organization

Each file should have a clear purpose.

Large files should remain logically organized.

Related functionality should remain together.

Unrelated functionality should not be mixed into the same module.

The project structure should remain consistent throughout development.

---

## Function Design

Functions should perform one clearly defined task.

Functions should:

- Have meaningful names.
- Accept only required parameters.
- Return predictable outputs.
- Avoid hidden side effects.
- Be easy to test.

Very large functions should be avoided whenever practical.

---

## Variable Naming

Variable names should describe their purpose.

Avoid abbreviations unless they are universally understood.

Good examples:

- pending_topics
- generated_html
- published_url
- article_title

Poor examples:

- data1
- temp
- obj
- val

Code should be self-explanatory whenever possible.

---

## Logging Standards

Important operations should be logged.

Logs should help identify:

- Workflow progress
- Success
- Warnings
- Failures
- Recovery attempts

Logs should provide useful information without becoming excessively verbose.

Sensitive information should never appear in logs.

---

## Error Handling

Expected failures should be handled gracefully.

Unexpected failures should:

- Produce meaningful logs.
- Preserve useful debugging information.
- Update execution status where appropriate.
- Avoid leaving the system in an inconsistent state.

Errors should never be silently ignored.

---

## Configuration Management

Configuration values should never be hardcoded.

Examples include:

- API keys
- Credentials
- Sheet IDs
- Blog IDs
- Bucket names
- Environment-specific settings

These values should remain in the project's configuration system.

---

## Security

Sensitive information must never be committed to source control.

Examples include:

- API keys
- Access tokens
- Service account credentials
- Passwords
- Private keys

The codebase should assume that repositories may eventually become public.

---

## Documentation

Complex logic should be documented.

Documentation should explain:

- Why the implementation exists.
- What problem it solves.
- Any important assumptions.
- Any important limitations.

Comments should explain intent rather than restate obvious code.

---

## Performance

Performance improvements should only be introduced when they provide measurable value.

Readable code should generally be preferred over micro-optimizations.

Premature optimization should be avoided.

---

## Dependency Management

Introduce new dependencies only when they provide clear value.

Before adding a dependency, determine whether the existing project already provides the required functionality.

Unnecessary dependencies increase maintenance complexity.

---

## Testing Mindset

Every change should be made with production reliability in mind.

Before considering a feature complete, verify that:

- Existing functionality still works.
- New functionality behaves as expected.
- Failure scenarios have been considered.
- Logging remains useful.
- No unintended side effects were introduced.

---

## Code Reviews

Before accepting any implementation, ask the following questions:

- Does the code solve the intended problem?
- Is the solution understandable?
- Is duplication avoided?
- Does it preserve existing behaviour?
- Does it introduce unnecessary complexity?
- Can another developer understand it quickly?
- Would this still make sense six months from now?

If the answer to any of these questions is no, the implementation should be improved before acceptance.

---

## Refactoring

Refactoring should only occur when one or more of the following conditions are true:

- It fixes a defect.
- It improves maintainability.
- It reduces duplication.
- It improves readability.
- It supports an approved requirement.

Refactoring should never occur solely because a different style is preferred.

---

## AI Development Rules

When generating code, the AI should:

- Read existing code before modifying it.
- Preserve existing behaviour.
- Modify the minimum amount of code necessary.
- Explain important changes before implementation.
- Avoid speculative improvements.
- Follow the approved roadmap.
- Respect the current Architecture Freeze.

The AI should never replace working implementations simply because another approach exists.

---

## Production Mindset

Every line of code should be written as though it will immediately execute in production.

Temporary shortcuts, experimental implementations, placeholder logic, and unfinished behaviour should never be committed as completed work.

Production reliability always takes priority over development speed.

---

## Change Policy

This document is governed by the current Architecture Freeze.

No coding standards defined here may be altered until the Architecture Freeze has been officially lifted by the project owner.

Minor clarifications, documentation corrections, and factual improvements are permitted provided they do not change the intent of these standards.

---

Version: 1.0

Status: Active

Last Updated: 2026-07-06

Owner: RemoteProstor