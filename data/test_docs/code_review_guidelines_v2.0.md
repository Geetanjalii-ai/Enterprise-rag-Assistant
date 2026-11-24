# Code Review Guidelines

**Company:** Meridian Software Services Pvt. Ltd.  
**Document ID:** ENG-GDE-001  
**Title:** Code Review Guidelines  
**Version:** 2.0  
**Effective date:** 2026-11-15  
**Owner:** Engineering  
**Applies to:** All engineers  

## Core Principles

Code reviews uphold software resilience, distribute domain knowledge, and enforce Meridian's architecture standards. Always review with constructive empathy.

## Pull Request Requirements

- **PR Sizing:** PRs should strictly contain under 350 lines of diff (excluding auto-generated code and test mocks).
- **Automated Verification:** All CI linting, unit test suites, security vulnerability scans, and typechecks must pass before requesting peer review.
- **AI-Assisted Pre-check:** Authors should run Meridian Code Assist to inspect security smells and edge cases prior to submitting.

## Review SLA and Approvals

- **Standard Reviews:** Reviewers must respond within 1 business day (24 hours).
- **Approval Count:** At least 1 senior peer approval is required for general feature code.
- **Sensitive Infrastructure:** Core financial ledgers, cryptographic auth flows, and data ingestion pipelines require 2 independent approvals, including one from a Principal Engineer or Department Head.
- **Resolution:** If discussion exceeds 3 iterations, schedule a quick 10-minute huddle with the Engineering Team Lead to resolve blockers.
