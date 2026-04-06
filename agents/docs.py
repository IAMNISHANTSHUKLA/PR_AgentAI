"""Documentation review agent — checks docs, comments, and API documentation."""

from typing import Optional
import config
from agents.base import BaseAgent


class DocumentationAgent(BaseAgent):
    """Reviews documentation completeness and accuracy in code changes."""

    def __init__(self):
        super().__init__(name="documentation", model=config.MODEL_FAST)

    def get_system_prompt(self) -> str:
        return """You are a technical writing expert reviewing code documentation.
Evaluate the pull request diff for documentation completeness, clarity,
and consistency with the team's documentation standards.

Focus on these areas:
- **Docstrings**: Missing, incomplete, or outdated function/class docstrings
- **Inline Comments**: Missing explanation for complex logic, magic numbers
- **README/Changelog**: Missing updates for new features or breaking changes
- **API Documentation**: Missing endpoint docs, parameter descriptions, examples
- **Type Annotations**: Missing or incorrect type hints that serve as documentation
- **Error Messages**: Unclear error messages that don't help debugging
- **TODO/FIXME/HACK**: Unresolved technical debt markers
- **Naming**: Variable/function names that don't clearly convey purpose
- **Architecture Docs**: Missing ADRs for significant design decisions

Be practical — don't demand JSDoc for trivial one-line functions, but do flag
missing documentation for public APIs, complex algorithms, and non-obvious logic.

Respond with this exact JSON structure:
{
  "summary": "Brief overall documentation assessment",
  "score": <0-100, where 100 is perfectly documented>,
  "findings": [
    {
      "severity": "critical|high|medium|low|info",
      "category": "Category name",
      "file": "filename from diff",
      "line": <line number or null>,
      "title": "Short title",
      "description": "What documentation is missing or incorrect",
      "suggestion": "Specific documentation to add, with example text"
    }
  ]
}"""

    def get_review_prompt(self, diff: str, context: str) -> str:
        prompt = f"""Review this pull request diff for documentation quality:

```diff
{diff}
```"""
        if context:
            prompt += f"""

The following are the team's documentation standards from Confluence. Flag any violations:

{context}"""
        return prompt

    def get_collection_name(self) -> Optional[str]:
        return config.COLLECTION_CONFLUENCE
