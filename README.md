# 🤖 PR AgentAI

**Multi-Agent Pull Request Review System** — powered by **LangGraph** orchestration and **Cerebras AI** inference.

An intelligent code review pipeline that runs three specialized AI agents (Security, Quality, Documentation) in parallel across your PR diffs, aggregates their findings with weighted scoring, and delivers a structured verdict — all in under 5 seconds.

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────────┐
                    │         PR AgentAI Pipeline          │
                    │         (LangGraph StateGraph)       │
                    └─────────────────────────────────────┘

                              ┌──────────┐
                              │  START   │
                              └────┬─────┘
                                   │
                              ┌────▼─────┐
                              │  Intake  │  ← Validates input, logs pipeline start
                              └────┬─────┘
                    ┌──────────────┼──────────────┐
                    │              │              │         ← Parallel Fan-Out
              ┌─────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
              │  Security  │ │ Quality  │ │   Docs     │
              │   Agent    │ │  Agent   │ │   Agent    │
              │ (llama3.1) │ │(llama3.1)│ │ (llama3.1) │
              └─────┬──────┘ └────┬─────┘ └─────┬──────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                   │              ← Fan-In (waits for all)
                            ┌──────▼──────┐
                            │  Aggregate  │  ← Weighted scoring (50/30/20)
                            └──────┬──────┘
                                   │
                            ┌──────▼──────┐
                            │   Verdict   │  ← approve / comment / request_changes
                            └──────┬──────┘
                                   │
                              ┌────▼─────┐
                              │   END    │
                              └──────────┘
```

### LangGraph State Machine

The pipeline uses a **compiled LangGraph `StateGraph`** with typed state and reducers:

```python
class PRReviewState(TypedDict):
    diff: str                                                    # Input PR diff
    pr_id: str                                                   # PR identifier
    agent_results: Annotated[list[dict], operator.add]           # Reducer: parallel append
    overall_score: int                                           # 0-100 weighted score
    total_findings: int                                          # Total issues found
    critical_findings: int                                       # Critical/high severity count
    verdict: str                                                 # approve|comment|request_changes
    overall_summary: str                                         # Human-readable summary
    duration_ms: float                                           # Pipeline execution time
```

The `operator.add` reducer on `agent_results` is the key — it allows all three parallel agent nodes to append their results without overwriting each other.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (tested on 3.14)
- **Cerebras API Key** — get one at [cerebras.ai](https://cerebras.ai)

### 1. Clone & Install

```bash
git clone https://github.com/your-username/PR_AgentAI.git
cd PR_AgentAI

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
CEREBRAS_API_KEY=csk-your-api-key-here
CEREBRAS_MODEL_FAST=llama3.1-8b
CEREBRAS_MODEL_DEEP=llama3.1-8b
CHROMADB_PERSIST_DIR=./chroma_db
LOG_LEVEL=INFO
AUDIT_LOG_FILE=./logs/audit.jsonl
```

### 3. Seed the Vector Store

```bash
python seed.py
```

This loads your coding standards and documentation into ChromaDB so agents can ground their reviews in your team's actual standards.

**Expected output:**
```
✅ Seeded 2 coding standards documents
✅ Seeded 1 Confluence documents
📊 Collections: ['coding_standards', 'confluence_docs']
   coding_standards: 2 chunks
   confluence_docs: 1 chunks
🎉 Vector store seeded successfully!
```

### 4. Run the Dashboard

```bash
python -m uvicorn web.app:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

### 5. Run via CLI

```bash
# Review a diff file with Rich formatted output
python main.py --diff data/sample_prs/vulnerable_api.diff

# Specify a PR ID
python main.py --diff data/sample_prs/clean_payment.diff --pr-id PR-42

# Get raw JSON output (for CI/CD integration)
python main.py --diff data/sample_prs/vulnerable_api.diff --json

# Verbose logging
python main.py --diff data/sample_prs/vulnerable_api.diff --log-level DEBUG
```

---

## 📁 Project Structure

```
PR_AgentAI/
├── .env                              # Environment variables (API keys, model config)
├── .gitignore                        # Protects secrets and build artifacts
├── requirements.txt                  # Python dependencies
├── config.py                         # Centralized configuration module
├── llm.py                            # Cerebras SDK client (retry, JSON parsing)
├── audit.py                          # JSONL structured audit logger
├── vectorstore.py                    # ChromaDB vector store (semantic search)
├── seed.py                           # Seeds ChromaDB with coding standards
├── main.py                           # CLI entry point (Rich formatted output)
│
├── agents/                           # Agent pipeline
│   ├── __init__.py
│   ├── base.py                       # Abstract BaseAgent class
│   ├── security.py                   # Security vulnerability scanner
│   ├── quality.py                    # Code quality & style reviewer
│   ├── docs.py                       # Documentation completeness checker
│   └── orchestrator.py               # ⭐ LangGraph StateGraph orchestrator
│
├── data/                             # Knowledge base & test data
│   ├── coding_standards/
│   │   ├── python_security.md        # Security coding standards
│   │   └── code_quality.md           # Quality & style standards
│   ├── confluence/
│   │   └── api_documentation_standards.md  # Documentation standards
│   └── sample_prs/
│       ├── vulnerable_api.diff       # Intentionally vulnerable (SQL injection, XSS, etc.)
│       └── clean_payment.diff        # Well-structured clean code
│
├── web/                              # Web dashboard
│   ├── app.py                        # FastAPI backend (8 endpoints)
│   ├── static/
│   │   ├── style.css                 # Premium dark-mode design system
│   │   └── app.js                    # Frontend logic (Mermaid graphs, animations)
│   └── templates/
│       └── index.html                # Dashboard HTML
│
├── chroma_db/                        # ChromaDB persistent storage (auto-created)
└── logs/                             # Audit logs (auto-created)
    └── audit.jsonl                   # Structured audit trail
```

---

## 🔧 Core Components

### 1. LLM Client (`llm.py`)

Wraps the Cerebras Cloud SDK with:
- **Exponential backoff retry** — 3 attempts with `1s → 2s → 4s` delays
- **JSON response parsing** — strips markdown fences, validates JSON
- **Singleton pattern** — single client instance reused across agents
- **Temperature 0.2** — low to prevent hallucinated library APIs

```python
from llm import get_llm

llm = get_llm()
response = llm.chat("You are a reviewer.", "Review this code...")
structured = llm.chat_json("You are a reviewer.", "Return findings as JSON...")
```

### 2. Agents (`agents/`)

Each agent extends `BaseAgent` and implements:

| Method | Purpose |
|---|---|
| `get_system_prompt()` | Expert persona + output JSON schema |
| `get_review_prompt()` | Builds the user prompt with diff + context |
| `get_collection_name()` | Which ChromaDB collection to query for RAG context |

**Agent details:**

| Agent | Focus | ChromaDB Collection | Model |
|---|---|---|---|
| **Security** | SQL injection, XSS, auth, secrets, SSRF, eval() | `coding_standards` | `llama3.1-8b` |
| **Quality** | SOLID, naming, error handling, complexity, testing | `coding_standards` | `llama3.1-8b` |
| **Documentation** | Docstrings, comments, README, API docs, ADRs | `confluence_docs` | `llama3.1-8b` |

### 3. LangGraph Orchestrator (`agents/orchestrator.py`)

The heart of the system — a compiled `StateGraph` that:

1. **Intake node** — validates input, logs pipeline start
2. **Parallel fan-out** — spawns security, quality, and docs agents simultaneously
3. **Fan-in** — waits for all three agents to complete
4. **Aggregate node** — weighted scoring (Security 50%, Quality 30%, Docs 20%)
5. **Verdict node** — determines approve/comment/request_changes

```python
from agents.orchestrator import Orchestrator

orchestrator = Orchestrator()
result = orchestrator.review(diff_text, pr_id="PR-123")
print(result.verdict)       # "approve" | "comment" | "request_changes"
print(result.overall_score) # 0-100
```

**Verdict Logic:**
| Condition | Verdict |
|---|---|
| Any critical/high findings OR score < 40 | `request_changes` |
| Score 40-69 | `comment` |
| Score ≥ 70 | `approve` |

### 4. Vector Store (`vectorstore.py`)

ChromaDB-backed semantic search that provides RAG context to agents:

- **Chunking** — splits documents into 512-word chunks with 50-word overlap
- **Cosine similarity** — matches PR diff content against coding standards
- **Persistent storage** — survives restarts at `./chroma_db/`

```python
from vectorstore import get_vectorstore

store = get_vectorstore()
hits = store.query("coding_standards", "SQL query construction", n_results=3)
```

### 5. Audit Logger (`audit.py`)

Every pipeline action is logged as structured JSONL:

```json
{
  "timestamp": "2026-04-06T10:06:32.123Z",
  "agent": "security",
  "action": "review_complete",
  "severity": "info",
  "pr_id": "PR-TEST-001",
  "duration_ms": 1842.31,
  "details": {"score": 15, "findings": 8}
}
```

Features:
- **Append-only JSONL** — tamper-evident audit trail
- **TimedAction context manager** — auto-logs duration
- **In-memory + file** — queryable in-process, persistent on disk

---

## 🌐 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Dashboard UI |
| `POST` | `/api/review` | Submit a PR diff for multi-agent review |
| `GET` | `/api/samples` | List available sample diffs |
| `POST` | `/api/samples/load` | Load a specific sample diff |
| `GET` | `/api/graph` | Get the Mermaid diagram of the LangGraph pipeline |
| `GET` | `/api/audit` | Query the audit trail (optional `?pr_id=` filter) |
| `GET` | `/api/vectorstore/status` | Check ChromaDB collection counts |
| `GET` | `/api/health` | System health check |

### Example: Submit a Review

```bash
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{"diff": "diff --git a/app.py...", "pr_id": "PR-42"}'
```

**Response:**
```json
{
  "pr_id": "PR-42",
  "verdict": "request_changes",
  "overall_score": 24,
  "overall_summary": "Overall Score: 24/100 | Verdict: REQUEST_CHANGES...",
  "total_findings": 12,
  "critical_findings": 5,
  "duration_ms": 3184.95,
  "agents": [
    {
      "agent": "security",
      "score": 15,
      "findings": [...],
      "duration_ms": 2100.0
    },
    ...
  ]
}
```

---

## 🎨 Web Dashboard

The dashboard features:
- **🔗 LangGraph Pipeline Visualization** — interactive Mermaid diagram of the agent graph
- **📊 Score Ring** — animated SVG ring showing overall score with color coding
- **📈 Agent Score Bars** — per-agent score breakdown
- **🔍 Findings Panel** — filterable by severity (critical/high/medium/low/info)
- **⏱️ Timing Stats** — per-agent and total execution time
- **🎯 Verdict Banner** — approve (green) / comment (yellow) / reject (red)
- **📄 Sample Loader** — preloaded sample diffs for demo

**Design:**
- Dark mode with glassmorphism effects
- Inter + JetBrains Mono typography
- Smooth micro-animations and transitions
- Fully responsive layout

---

## 📋 Adding Custom Standards

Drop Markdown files into the appropriate directory, then re-seed:

```bash
# Add security/quality standards
cp your-team-standards.md data/coding_standards/

# Add documentation standards (from Confluence etc.)
cp your-doc-standards.md data/confluence/

# Re-seed the vector store
python seed.py
```

Agents will automatically use these standards as RAG context during reviews.

---

## 🚢 Deployment

### Production with Uvicorn

```bash
# Production mode (no reload, multiple workers)
uvicorn web.app:app --host 0.0.0.0 --port 8000 --workers 4

# With SSL
uvicorn web.app:app --host 0.0.0.0 --port 443 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python seed.py
EXPOSE 8000
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t pr-agentai .
docker run -p 8000:8000 --env-file .env pr-agentai
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `CEREBRAS_API_KEY` | (required) | Your Cerebras API key |
| `CEREBRAS_MODEL_FAST` | `llama3.1-8b` | Fast model for quality/docs agents |
| `CEREBRAS_MODEL_DEEP` | `llama3.1-8b` | Deep model for security agent |
| `CHROMADB_PERSIST_DIR` | `./chroma_db` | ChromaDB storage directory |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `AUDIT_LOG_FILE` | `./logs/audit.jsonl` | Audit log file path |

---

## 🧪 Testing

### Run a review on the intentionally-vulnerable sample:

```bash
python main.py --diff data/sample_prs/vulnerable_api.diff
```

**Expected findings:** SQL injection, XSS, hardcoded API keys, MD5 password hashing, `eval()` of user input, path traversal, missing authentication, debug mode in production.

### Run a review on clean code:

```bash
python main.py --diff data/sample_prs/clean_payment.diff
```

**Expected result:** High score (70+), few or no critical findings.

### Health check:

```bash
curl http://localhost:8000/api/health
```

---

## 🔑 Key Design Decisions

| Decision | Rationale |
|---|---|
| **LangGraph over raw threads** | Proper stateful orchestration, typed state, reducers for parallel aggregation, visual graph export |
| **Temperature = 0.2** | Prevents the model from hallucinating library APIs that don't exist |
| **Weighted scoring (50/30/20)** | Security issues are harder to catch and more impactful than style nits |
| **ChromaDB for RAG** | Agents ground reviews in actual team standards, not generic advice |
| **JSONL audit trail** | Append-only, structured, greppable, tamper-evident |
| **Cerebras inference** | Fast enough (~3s total) that the multi-agent pipeline feels real-time |

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `cerebras-cloud-sdk` | Cerebras AI inference API |
| `langgraph` | Stateful graph-based agent orchestration |
| `langchain-core` | Core abstractions for LangGraph |
| `chromadb` | Vector database for RAG context |
| `fastapi` | Web API framework |
| `uvicorn` | ASGI server |
| `jinja2` | HTML templating |
| `rich` | Terminal formatting for CLI |
| `pydantic` | Data validation |
| `python-dotenv` | Environment variable loading |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with ❤️ using [LangGraph](https://github.com/langchain-ai/langgraph) + [Cerebras](https://cerebras.ai)
