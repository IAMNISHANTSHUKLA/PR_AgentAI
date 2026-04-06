"""Structured audit logging for agent actions.

Every agent action is logged as a JSON-lines entry so the full review
pipeline is traceable and auditable.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import config

logger = logging.getLogger(__name__)


class AuditLogger:
    """Append-only JSONL audit logger."""

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = Path(log_path or config.AUDIT_LOG_FILE)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[dict] = []
        logger.info(f"AuditLogger writing to {self.log_path}")

    def log(
        self,
        agent: str,
        action: str,
        details: Any = None,
        severity: str = "info",
        pr_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> dict:
        """Log a single audit event."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "action": action,
            "severity": severity,
            "pr_id": pr_id,
            "duration_ms": round(duration_ms, 2) if duration_ms else None,
            "details": details,
        }
        self._entries.append(entry)

        # Append to file
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

        log_fn = getattr(logger, severity, logger.info)
        log_fn(f"[AUDIT] {agent}/{action}: {json.dumps(details, default=str)[:200]}")
        return entry

    def get_entries(
        self,
        agent: Optional[str] = None,
        pr_id: Optional[str] = None,
    ) -> list[dict]:
        """Filter in-memory entries."""
        results = self._entries
        if agent:
            results = [e for e in results if e["agent"] == agent]
        if pr_id:
            results = [e for e in results if e["pr_id"] == pr_id]
        return results

    def get_summary(self, pr_id: Optional[str] = None) -> dict:
        """Return a summary of the audit trail."""
        entries = self.get_entries(pr_id=pr_id)
        agents = set(e["agent"] for e in entries)
        severities = {}
        for e in entries:
            severities[e["severity"]] = severities.get(e["severity"], 0) + 1
        total_ms = sum(e["duration_ms"] for e in entries if e["duration_ms"])
        return {
            "total_events": len(entries),
            "agents_involved": list(agents),
            "severity_counts": severities,
            "total_duration_ms": round(total_ms, 2),
        }


class TimedAction:
    """Context manager that auto-logs duration."""

    def __init__(self, audit: AuditLogger, agent: str, action: str, **kwargs):
        self.audit = audit
        self.agent = agent
        self.action = action
        self.kwargs = kwargs
        self._start = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.perf_counter() - self._start) * 1000
        severity = "error" if exc_type else "info"
        details = self.kwargs.get("details", {})
        if exc_type:
            details["error"] = str(exc_val)
        self.audit.log(
            agent=self.agent,
            action=self.action,
            details=details,
            severity=severity,
            duration_ms=duration,
            pr_id=self.kwargs.get("pr_id"),
        )


# ── Convenience singleton ──────────────────────────────────────────────
_audit: Optional[AuditLogger] = None


def get_audit() -> AuditLogger:
    global _audit
    if _audit is None:
        _audit = AuditLogger()
    return _audit
