"""Base agent class for the multi-agent PR review pipeline."""

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from llm import CerebrasLLM, get_llm
from audit import AuditLogger, get_audit, TimedAction
from vectorstore import VectorStore, get_vectorstore

logger = logging.getLogger(__name__)


class ReviewFinding:
    """A single finding from an agent review."""

    def __init__(
        self,
        severity: str,      # critical | high | medium | low | info
        category: str,       # e.g. "SQL Injection", "Missing Docstring"
        file: str,
        line: Optional[int],
        title: str,
        description: str,
        suggestion: str = "",
    ):
        self.severity = severity
        self.category = category
        self.file = file
        self.line = line
        self.title = title
        self.description = description
        self.suggestion = suggestion

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "file": self.file,
            "line": self.line,
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
        }


class AgentResult:
    """The complete output of an agent review."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.findings: list[ReviewFinding] = []
        self.summary: str = ""
        self.score: int = 100  # 0-100, starts perfect
        self.duration_ms: float = 0.0
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "agent": self.agent_name,
            "score": self.score,
            "summary": self.summary,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error,
        }


class BaseAgent(ABC):
    """Abstract base class for review agents."""

    def __init__(self, name: str, model: Optional[str] = None):
        self.name = name
        self.llm = get_llm(model)
        self.audit = get_audit()
        self.vectorstore = get_vectorstore()
        logger.info(f"Agent '{self.name}' initialised")

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        ...

    @abstractmethod
    def get_review_prompt(self, diff: str, context: str) -> str:
        """Build the user prompt for reviewing a PR diff."""
        ...

    @abstractmethod
    def get_collection_name(self) -> Optional[str]:
        """Return the vector store collection to query for context. None = skip."""
        ...

    def review(self, diff: str, pr_id: str = "unknown") -> AgentResult:
        """Run the full review pipeline: context retrieval → LLM → parse."""
        result = AgentResult(self.name)
        start = time.perf_counter()

        try:
            with TimedAction(self.audit, self.name, "review_start", pr_id=pr_id):
                # 1. Retrieve relevant context from vector store
                context = self._retrieve_context(diff)

                # 2. Build prompts
                system_prompt = self.get_system_prompt()
                user_prompt = self.get_review_prompt(diff, context)

                # 3. Call LLM
                self.audit.log(self.name, "llm_call", pr_id=pr_id, details={"model": self.llm.model})
                raw_response = self.llm.chat_json(system_prompt, user_prompt)

                # 4. Parse response
                result = self._parse_response(raw_response, result)

                self.audit.log(
                    self.name, "review_complete", pr_id=pr_id,
                    details={"score": result.score, "findings": len(result.findings)},
                )

        except Exception as e:
            result.error = str(e)
            result.score = 0
            self.audit.log(
                self.name, "review_error", pr_id=pr_id,
                severity="error", details={"error": str(e)},
            )
            logger.error(f"Agent '{self.name}' failed: {e}", exc_info=True)

        result.duration_ms = (time.perf_counter() - start) * 1000
        return result

    def _retrieve_context(self, diff: str) -> str:
        """Query the vector store for relevant standards/docs."""
        collection = self.get_collection_name()
        if not collection:
            return ""

        try:
            # Use first 500 chars of diff as query
            query = diff[:500]
            hits = self.vectorstore.query(collection, query, n_results=3)
            if hits:
                context_parts = [h["content"] for h in hits]
                context = "\n\n---\n\n".join(context_parts)
                logger.debug(f"Retrieved {len(hits)} context chunks for '{self.name}'")
                return context
        except Exception as e:
            logger.warning(f"Context retrieval failed for '{self.name}': {e}")

        return ""

    def _parse_response(self, data: dict, result: AgentResult) -> AgentResult:
        """Parse structured JSON response into AgentResult."""
        result.summary = data.get("summary", "No summary provided.")
        result.score = max(0, min(100, data.get("score", 50)))

        for finding_data in data.get("findings", []):
            finding = ReviewFinding(
                severity=finding_data.get("severity", "info"),
                category=finding_data.get("category", "General"),
                file=finding_data.get("file", "unknown"),
                line=finding_data.get("line"),
                title=finding_data.get("title", "Finding"),
                description=finding_data.get("description", ""),
                suggestion=finding_data.get("suggestion", ""),
            )
            result.findings.append(finding)

        return result
