"""Code quality review agent — evaluates style, structure, and maintainability."""

from typing import Optional
import config
from agents.base import BaseAgent


class QualityAgent(BaseAgent):
    """Reviews code quality, style, and engineering best practices."""

    def __init__(self):
        super().__init__(name="quality", model=config.MODEL_FAST)

    def get_system_prompt(self) -> str:
        return """You are a senior software engineer performing a code quality review.
Evaluate the pull request diff for engineering best practices, code quality,
and maintainability.

Focus on these areas:
- **Code Style**: Naming conventions, formatting consistency, idiomatic patterns
- **Design Patterns**: SOLID principles, appropriate abstractions, DRY violations
- **Error Handling**: Missing try/catch, swallowed exceptions, unclear error messages
- **Performance**: N+1 queries, unnecessary allocations, inefficient algorithms
- **Testing**: Missing test coverage, untestable code, fragile tests
- **Complexity**: Cyclomatic complexity, deep nesting, god functions
- **Type Safety**: Missing type hints, any-type abuse, unsafe casts
- **API Design**: Breaking changes, inconsistent interfaces, missing validation
- **Concurrency**: Race conditions, deadlocks, unsafe shared state
- **Logging & Observability**: Missing logs, excessive logging, no structured logging

Be pragmatic — focus on issues that actually impact maintainability and reliability,
not pedantic style nits.

Respond with this exact JSON structure:
{
  "summary": "Brief overall quality assessment",
  "score": <0-100, where 100 is perfect quality>,
  "findings": [
    {
      "severity": "critical|high|medium|low|info",
      "category": "Category name",
      "file": "filename from diff",
      "line": <line number or null>,
      "title": "Short title",
      "description": "Detailed explanation of the issue",
      "suggestion": "Specific improvement with code if applicable"
    }
  ]
}"""

    def get_review_prompt(self, diff: str, context: str) -> str:
        prompt = f"""Review this pull request diff for code quality:

```diff
{diff}
```"""
        if context:
            prompt += f"""

The following are the team's coding standards. Flag any violations:

{context}"""
        return prompt

    def get_collection_name(self) -> Optional[str]:
        return config.COLLECTION_CODING_STANDARDS
