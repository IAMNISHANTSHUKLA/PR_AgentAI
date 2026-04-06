# API Documentation Standards — Confluence

## Overview
All internal APIs must follow these documentation standards to ensure consistency
and ease of onboarding for new team members.

## Endpoint Documentation Requirements
Every REST endpoint must document:
1. HTTP method and path
2. Authentication requirements
3. Request parameters (query, path, body) with types and validation rules
4. Response format with example JSON
5. Error responses with status codes and error message format
6. Rate limiting information

## Code Documentation
- All modules must have a module-level docstring explaining purpose and usage.
- Complex algorithms must include inline comments explaining the approach.
- TODO comments must include a Jira ticket reference (e.g., `TODO(PROJ-123): ...`).
- Deprecated code must use `@deprecated` decorator with migration instructions.

## Changelog Requirements
- Every PR that changes user-facing behavior must update CHANGELOG.md.
- Use Keep a Changelog format (Added, Changed, Deprecated, Removed, Fixed, Security).
- Include migration instructions for breaking changes.

## Architecture Decision Records (ADRs)
- Significant design decisions must be documented as ADRs.
- ADRs follow the format: Context, Decision, Consequences.
- Store ADRs in the `docs/adr/` directory.
- Once accepted, ADRs are immutable — create new ADRs to supersede old ones.

## README Requirements
- Every service must have a README.md with:
  - Service description and purpose
  - Setup instructions (local development)
  - Environment variable reference
  - API endpoint summary
  - Deployment instructions
