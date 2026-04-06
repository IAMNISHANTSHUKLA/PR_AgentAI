"""LangGraph-based orchestrator — proper stateful graph orchestration for the
multi-agent PR review pipeline.

Uses LangGraph's StateGraph with parallel fan-out so all three review agents
(security, quality, documentation) execute as concurrent graph nodes, with
results aggregated through a reducer into a final verdict node.

Graph Structure:
    START → intake → [security, quality, documentation] (parallel) → aggregate → verdict → END
"""

import logging
import time
import operator
from typing import Annotated, Optional, TypedDict

from langgraph.graph import StateGraph, START, END

from agents.base import AgentResult
from agents.security import SecurityAgent
from agents.quality import QualityAgent
from agents.docs import DocumentationAgent
from audit import get_audit

import config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# State Schema — TypedDict with reducers for parallel aggregation
# ═══════════════════════════════════════════════════════════════════════

class PRReviewState(TypedDict):
    """Shared state flowing through the LangGraph pipeline.

    The `agent_results` key uses `operator.add` as a reducer so that
    each parallel agent node can append its result without overwriting
    results from other agents.
    """
    # Input
    diff: str
    pr_id: str

    # Accumulated across parallel nodes via reducer
    agent_results: Annotated[list[dict], operator.add]

    # Set by the aggregate node
    overall_score: int
    total_findings: int
    critical_findings: int
    verdict: str          # approve | comment | request_changes
    overall_summary: str
    duration_ms: float


# ═══════════════════════════════════════════════════════════════════════
# Node Functions
# ═══════════════════════════════════════════════════════════════════════

# Lazy-initialised agent singletons (created once per process)
_agents: dict = {}


def _get_agent(name: str):
    """Get or create an agent singleton."""
    if name not in _agents:
        if name == "security":
            _agents[name] = SecurityAgent()
        elif name == "quality":
            _agents[name] = QualityAgent()
        elif name == "documentation":
            _agents[name] = DocumentationAgent()
    return _agents[name]


def intake_node(state: PRReviewState) -> dict:
    """Intake node — validates input and logs pipeline start."""
    audit = get_audit()
    audit.log("orchestrator", "pipeline_start", pr_id=state["pr_id"], details={
        "diff_length": len(state["diff"]),
        "agents": config.AGENT_NAMES,
        "framework": "langgraph",
    })
    logger.info(f"[LangGraph] Pipeline started for {state['pr_id']} ({len(state['diff'])} chars)")
    # Pass through — no state mutation needed, just logging
    return {}


def security_node(state: PRReviewState) -> dict:
    """Security review agent node — uses deeper model."""
    agent = _get_agent("security")
    result = agent.review(state["diff"], pr_id=state["pr_id"])
    logger.info(f"[LangGraph] Security agent done — score={result.score}, findings={len(result.findings)}")
    return {"agent_results": [result.to_dict()]}


def quality_node(state: PRReviewState) -> dict:
    """Code quality review agent node — uses fast model."""
    agent = _get_agent("quality")
    result = agent.review(state["diff"], pr_id=state["pr_id"])
    logger.info(f"[LangGraph] Quality agent done — score={result.score}, findings={len(result.findings)}")
    return {"agent_results": [result.to_dict()]}


def documentation_node(state: PRReviewState) -> dict:
    """Documentation review agent node — uses fast model."""
    agent = _get_agent("documentation")
    result = agent.review(state["diff"], pr_id=state["pr_id"])
    logger.info(f"[LangGraph] Documentation agent done — score={result.score}, findings={len(result.findings)}")
    return {"agent_results": [result.to_dict()]}


def aggregate_node(state: PRReviewState) -> dict:
    """Aggregate all agent results into overall scores and verdict.

    Applies weighted scoring:
        Security:       50%
        Quality:        30%
        Documentation:  20%
    """
    results = state["agent_results"]
    weights = {"security": 0.5, "quality": 0.3, "documentation": 0.2}

    total_weight = 0
    weighted_score = 0
    total_findings = 0
    critical_findings = 0

    for agent_result in results:
        w = weights.get(agent_result["agent"], 0.2)
        weighted_score += agent_result["score"] * w
        total_weight += w
        total_findings += agent_result["finding_count"]
        critical_findings += sum(
            1 for f in agent_result["findings"]
            if f["severity"] in ("critical", "high")
        )

    overall_score = round(weighted_score / total_weight) if total_weight else 0

    logger.info(f"[LangGraph] Aggregation complete — score={overall_score}, findings={total_findings}")
    return {
        "overall_score": overall_score,
        "total_findings": total_findings,
        "critical_findings": critical_findings,
    }


def verdict_node(state: PRReviewState) -> dict:
    """Determine the final verdict based on aggregated scores."""
    score = state["overall_score"]
    critical = state["critical_findings"]

    # Decision logic
    if critical > 0 or score < 40:
        verdict = "request_changes"
    elif score < 70:
        verdict = "comment"
    else:
        verdict = "approve"

    # Build summary
    agent_summaries = []
    for r in state["agent_results"]:
        icon = "✅" if r["score"] >= 70 else "⚠️" if r["score"] >= 40 else "❌"
        agent_summaries.append(f"{icon} **{r['agent'].title()}**: {r['score']}/100")

    summary = (
        f"Overall Score: {score}/100 | Verdict: {verdict.upper()}\n\n"
        + "\n".join(agent_summaries)
        + f"\n\nTotal findings: {state['total_findings']} "
        f"({critical} critical/high)"
    )

    audit = get_audit()
    audit.log("orchestrator", "pipeline_complete", pr_id=state["pr_id"], details={
        "overall_score": score,
        "verdict": verdict,
        "total_findings": state["total_findings"],
    })

    logger.info(f"[LangGraph] Verdict: {verdict} (score={score})")
    return {
        "verdict": verdict,
        "overall_summary": summary,
    }


# ═══════════════════════════════════════════════════════════════════════
# Graph Assembly
# ═══════════════════════════════════════════════════════════════════════

def build_review_graph() -> StateGraph:
    """Construct the LangGraph StateGraph for the PR review pipeline.

    Graph topology:
        START → intake → security  ─┐
                       → quality   ─┤ (parallel fan-out)
                       → documentation ─┘
                                    ↓
                              aggregate → verdict → END
    """
    graph = StateGraph(PRReviewState)

    # Register nodes
    graph.add_node("intake", intake_node)
    graph.add_node("security", security_node)
    graph.add_node("quality", quality_node)
    graph.add_node("documentation", documentation_node)
    graph.add_node("aggregate", aggregate_node)
    graph.add_node("verdict", verdict_node)

    # Edges: START → intake
    graph.add_edge(START, "intake")

    # Parallel fan-out: intake → [security, quality, documentation]
    graph.add_edge("intake", "security")
    graph.add_edge("intake", "quality")
    graph.add_edge("intake", "documentation")

    # Fan-in: all agents → aggregate
    graph.add_edge("security", "aggregate")
    graph.add_edge("quality", "aggregate")
    graph.add_edge("documentation", "aggregate")

    # aggregate → verdict → END
    graph.add_edge("aggregate", "verdict")
    graph.add_edge("verdict", END)

    return graph


# ═══════════════════════════════════════════════════════════════════════
# Compiled Graph & Public API
# ═══════════════════════════════════════════════════════════════════════

# Compile once at module level for reuse
_compiled_graph = None


def get_compiled_graph():
    """Get or compile the review graph (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_review_graph()
        _compiled_graph = graph.compile()
        logger.info("[LangGraph] Review graph compiled successfully")
    return _compiled_graph


class OrchestratorResult:
    """Aggregated result — compatible API with the web/CLI layer."""

    def __init__(self):
        self.results: list[dict] = []
        self.overall_score: int = 100
        self.overall_summary: str = ""
        self.total_findings: int = 0
        self.critical_findings: int = 0
        self.duration_ms: float = 0.0
        self.pr_id: str = ""
        self.verdict: str = "approve"

    def to_dict(self) -> dict:
        return {
            "pr_id": self.pr_id,
            "verdict": self.verdict,
            "overall_score": self.overall_score,
            "overall_summary": self.overall_summary,
            "total_findings": self.total_findings,
            "critical_findings": self.critical_findings,
            "duration_ms": round(self.duration_ms, 2),
            "agents": self.results,
        }


class Orchestrator:
    """LangGraph-powered orchestrator for the multi-agent PR review pipeline.

    Uses a compiled StateGraph that fans out to security, quality, and
    documentation agents in parallel, then aggregates and produces a verdict.
    """

    def __init__(self):
        self.graph = get_compiled_graph()
        self.audit = get_audit()
        logger.info("[LangGraph] Orchestrator initialised with compiled graph")

    def review(self, diff: str, pr_id: str = "PR-001") -> OrchestratorResult:
        """Run the full LangGraph review pipeline."""
        start = time.perf_counter()

        # Invoke the graph
        initial_state: PRReviewState = {
            "diff": diff,
            "pr_id": pr_id,
            "agent_results": [],
            "overall_score": 0,
            "total_findings": 0,
            "critical_findings": 0,
            "verdict": "comment",
            "overall_summary": "",
            "duration_ms": 0.0,
        }

        final_state = self.graph.invoke(initial_state)

        # Build result object
        result = OrchestratorResult()
        result.pr_id = pr_id
        result.results = final_state["agent_results"]
        result.overall_score = final_state["overall_score"]
        result.overall_summary = final_state["overall_summary"]
        result.total_findings = final_state["total_findings"]
        result.critical_findings = final_state["critical_findings"]
        result.verdict = final_state["verdict"]
        result.duration_ms = (time.perf_counter() - start) * 1000

        return result


def get_graph_visualization() -> str:
    """Return a Mermaid diagram string of the review graph for the dashboard."""
    return """graph TD
    START([Start]) --> intake[📥 Intake & Validate]
    intake --> security[🔒 Security Agent<br/>Deep Model]
    intake --> quality[📐 Quality Agent<br/>Fast Model]
    intake --> docs[📝 Documentation Agent<br/>Fast Model]
    security --> aggregate[📊 Aggregate Scores]
    quality --> aggregate
    docs --> aggregate
    aggregate --> verdict{🏛️ Verdict}
    verdict -->|approve| approve_end([✅ Approve])
    verdict -->|comment| comment_end([⚠️ Comment])
    verdict -->|reject| reject_end([❌ Request Changes])

    style intake fill:#1a1a2e,stroke:#6366f1,color:#f0f0f5
    style security fill:#1a1a2e,stroke:#ef4444,color:#f0f0f5
    style quality fill:#1a1a2e,stroke:#22d3ee,color:#f0f0f5
    style docs fill:#1a1a2e,stroke:#eab308,color:#f0f0f5
    style aggregate fill:#1a1a2e,stroke:#6366f1,color:#f0f0f5
    style verdict fill:#1a1a2e,stroke:#a855f7,color:#f0f0f5"""
