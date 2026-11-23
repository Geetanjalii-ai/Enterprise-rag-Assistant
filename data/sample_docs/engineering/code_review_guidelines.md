# Code Review Guidelines

**Company:** Meridian Software Services Pvt. Ltd.  
**Document ID:** ENG-GDE-001  
**Version:** 1.3  
**Effective date:** 2026-01-01  
**Owner:** Engineering  
**Applies to:** All engineers  

## Principles

Code review improves quality, spreads knowledge and keeps the codebase consistent. Be kind, be specific and focus on the code, not the person.

## Rules for authors

- Keep pull requests small, at most 400 changed lines where possible.
- Write a clear description: what changed, why, and how it was tested.
- All automated checks must pass before you ask for review.
- Link the ticket in the description.

## Rules for reviewers

- Respond to a review request within 1 working day.
- Check correctness, tests, readability, security and performance.
- Mark comments as blocking or as a suggestion.
- Approve only when you would be comfortable maintaining the code yourself.

## Approvals

- At least 1 approval is required to merge.
- Changes to payments, authentication or customer data need 2 approvals, one from a senior engineer.
- Never merge your own pull request.

## Disagreements

If author and reviewer disagree after two rounds, ask the team lead to decide.
