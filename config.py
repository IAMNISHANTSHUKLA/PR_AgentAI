"""Centralized configuration for PR AgentAI."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
CHROMA_PERSIST_DIR = os.getenv("CHROMADB_PERSIST_DIR", str(BASE_DIR / "chroma_db"))
AUDIT_LOG_FILE = os.getenv("AUDIT_LOG_FILE", str(BASE_DIR / "logs" / "audit.jsonl"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── Cerebras ────────────────────────────────────────────────────────────
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
MODEL_FAST = os.getenv("CEREBRAS_MODEL_FAST", "llama3.1-8b")
MODEL_DEEP = os.getenv("CEREBRAS_MODEL_DEEP", "qwen-3-235b-a22b-instruct-2507")

# ── LLM Parameters ─────────────────────────────────────────────────────
LLM_TEMPERATURE = 0.2          # Low temp to prevent hallucinated APIs
LLM_MAX_TOKENS = 4096
LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_DELAY = 1.0    # seconds, exponential backoff base

# ── Agent Configuration ────────────────────────────────────────────────
AGENT_NAMES = ["security", "quality", "documentation"]
ORCHESTRATOR_TIMEOUT = 120     # seconds per agent

# ── Vector Store ────────────────────────────────────────────────────────
COLLECTION_CODING_STANDARDS = "coding_standards"
COLLECTION_CONFLUENCE = "confluence_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # ChromaDB default
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
