"""Security review agent — scans PR diffs for vulnerabilities and security anti-patterns.

Uses the deeper Maverick model by default because security analysis
requires careful reasoning over edge cases.
"""

from typing import Optional
import config
from agents.base import BaseAgent


class SecurityAgent(BaseAgent):
    """Identifies security vulnerabilities in code changes."""

    def __init__(self):
        # Security gets the deeper model for more careful reasoning
        super().__init__(name="security", model=config.MODEL_DEEP)

    def get_system_prompt(self) -> str:
        return """You are an expert application security engineer performing a code review.
Your job is to identify security vulnerabilities, misconfigurations, and anti-patterns
in the provided pull request diff.

Focus on these categories:
- **Injection Flaws**: SQL injection, command injection, XSS, template injection
- **Authentication & Authorization**: Missing auth checks, hardcoded credentials, weak tokens
- **Data Exposure**: Sensitive data in logs, unencrypted secrets, PII leaks
- **Cryptographic Issues**: Weak algorithms, improper key management, missing TLS
- **Input Validation**: Missing sanitization, buffer overflows, path traversal
- **Dependency Risks**: Known vulnerable packages, outdated libraries
- **Configuration**: Debug modes in production, permissive CORS, missing security headers
- **Race Conditions & TOCTOU**: Unsafe concurrent access patterns
- **Deserialization**: Unsafe deserialization of user input

For each finding, assess its real-world exploitability — don't flag theoretical issues
that can't actually be exploited in context.

Respond with this exact JSON structure:
{
  "summary": "Brief overall security assessment",
  "score": <0-100, where 100 is perfectly secure>,
  "findings": [
    {
      "severity": "critical|high|medium|low|info",
      "category": "Category name",
      "file": "filename from diff",
      "line": <line number or null>,
      "title": "Short title",
      "description": "Detailed explanation of the vulnerability",
      "suggestion": "Specific fix recommendation with code if applicable"
    }
  ]
}"""

    def get_review_prompt(self, diff: str, context: str) -> str:
        prompt = f"""Review this pull request diff for security vulnerabilities:

```diff
{diff}
```"""
        if context:
            prompt += f"""

The following are the team's security coding standards. Flag any violations:

{context}"""
        return prompt

    def get_collection_name(self) -> Optional[str]:
        return config.COLLECTION_CODING_STANDARDS
