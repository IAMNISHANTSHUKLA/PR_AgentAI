# Python Security Coding Standards

## Authentication & Authorization
- All API endpoints MUST require authentication unless explicitly marked as public.
- Use bcrypt with a minimum cost factor of 12 for password hashing. Never use MD5 or SHA-1 for passwords.
- JWT tokens must have an expiration time of no more than 1 hour for access tokens. Refresh tokens may last up to 7 days.
- Always validate JWT signatures server-side. Never trust client-supplied tokens without verification.
- Implement role-based access control (RBAC) for all administrative endpoints.

## Input Validation
- All user input MUST be validated on the server side, regardless of client-side validation.
- Use parameterized queries for ALL database operations. Raw string concatenation in SQL queries is strictly forbidden.
- Sanitize all user input before rendering in HTML to prevent XSS attacks.
- Validate file upload types using magic bytes, not just file extensions.
- Limit request body sizes to prevent denial-of-service attacks.

## Secrets Management
- Never hardcode API keys, passwords, or tokens in source code.
- Use environment variables or a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault) for all credentials.
- Rotate API keys and credentials at least every 90 days.
- Never log sensitive data including passwords, tokens, or PII.

## Error Handling
- Never expose stack traces or internal error details to end users.
- Log detailed errors server-side with structured logging.
- Return generic error messages to clients with appropriate HTTP status codes.
- Implement global exception handlers to catch unhandled errors.

## Dependencies
- Pin all dependency versions in requirements.txt.
- Run `pip-audit` or `safety check` as part of CI/CD pipeline.
- Update dependencies monthly. Critical security patches must be applied within 48 hours.

## API Security
- Implement rate limiting on all public-facing endpoints.
- Use HTTPS everywhere. HTTP must redirect to HTTPS.
- Set appropriate CORS headers — never use wildcard (*) in production.
- Add security headers: Content-Security-Policy, X-Frame-Options, X-Content-Type-Options.
