"""FastAPI web application for the PR AgentAI dashboard."""

import sys
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.orchestrator import Orchestrator, get_graph_visualization
from audit import get_audit
from vectorstore import get_vectorstore
import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s │ %(name)-20s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="PR AgentAI",
    description="Multi-Agent PR Review System powered by Cerebras",
    version="1.0.0",
)

# Static files and templates
web_dir = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(web_dir / "templates"))

# Orchestrator (lazy init)
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


# ── Pydantic Models ────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    diff: str
    pr_id: str = "PR-001"


class SampleRequest(BaseModel):
    sample: str  # filename of sample diff


# ── Routes ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the main dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/review")
async def review_pr(payload: ReviewRequest):
    """Submit a PR diff for multi-agent review."""
    if not payload.diff.strip():
        raise HTTPException(status_code=400, detail="Diff cannot be empty")

    if len(payload.diff) > 100_000:
        raise HTTPException(status_code=400, detail="Diff exceeds 100KB limit")

    orchestrator = get_orchestrator()
    result = orchestrator.review(payload.diff, pr_id=payload.pr_id)
    return JSONResponse(content=result.to_dict())


@app.get("/api/samples")
async def list_samples():
    """List available sample PR diffs."""
    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample_prs"
    samples = []
    if sample_dir.exists():
        for f in sorted(sample_dir.glob("*.diff")):
            content = f.read_text(encoding="utf-8")
            samples.append({
                "name": f.stem.replace("_", " ").title(),
                "filename": f.name,
                "size": len(content),
                "preview": content[:200] + "..." if len(content) > 200 else content,
            })
    return {"samples": samples}


@app.post("/api/samples/load")
async def load_sample(payload: SampleRequest):
    """Load a sample PR diff."""
    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample_prs"
    sample_path = sample_dir / payload.sample
    if not sample_path.exists() or not sample_path.suffix == ".diff":
        raise HTTPException(status_code=404, detail="Sample not found")
    content = sample_path.read_text(encoding="utf-8")
    return {"diff": content, "filename": payload.sample}


@app.get("/api/audit")
async def get_audit_trail(pr_id: Optional[str] = None):
    """Get the audit trail."""
    audit = get_audit()
    entries = audit.get_entries(pr_id=pr_id)
    summary = audit.get_summary(pr_id=pr_id)
    return {"entries": entries[-50:], "summary": summary}  # Last 50 entries


@app.get("/api/vectorstore/status")
async def vectorstore_status():
    """Check vector store status."""
    store = get_vectorstore()
    collections = {}
    for name in [config.COLLECTION_CODING_STANDARDS, config.COLLECTION_CONFLUENCE]:
        collections[name] = store.collection_count(name)
    return {"collections": collections, "persist_dir": store.persist_dir}


@app.get("/api/graph")
async def graph_visualization():
    """Return the Mermaid diagram of the LangGraph review pipeline."""
    return {"mermaid": get_graph_visualization()}


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "framework": "LangGraph",
        "model_fast": config.MODEL_FAST,
        "model_deep": config.MODEL_DEEP,
        "api_key_set": bool(config.CEREBRAS_API_KEY),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
