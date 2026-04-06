"""ChromaDB vector store for coding standards and Confluence docs.

Provides semantic search over organizational knowledge so agents can
ground their reviews in actual team standards rather than generic advice.
"""

import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

import config

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages ChromaDB collections for the PR review pipeline."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or config.CHROMA_PERSIST_DIR
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB initialised at {self.persist_dir}")

    def get_or_create_collection(self, name: str):
        """Get or create a named collection."""
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict],
        ids: list[str],
    ):
        """Add documents to a collection with chunking."""
        collection = self.get_or_create_collection(collection_name)
        
        all_chunks = []
        all_metas = []
        all_ids = []

        for doc, meta, doc_id in zip(documents, metadatas, ids):
            chunks = self._chunk_text(doc)
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metas.append({**meta, "chunk_index": i, "total_chunks": len(chunks)})
                all_ids.append(f"{doc_id}_chunk_{i}")

        if all_chunks:
            collection.add(
                documents=all_chunks,
                metadatas=all_metas,
                ids=all_ids,
            )
            logger.info(
                f"Added {len(all_chunks)} chunks from {len(documents)} docs "
                f"to collection '{collection_name}'"
            )

    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
    ) -> list[dict]:
        """Semantic search over a collection."""
        collection = self.get_or_create_collection(collection_name)
        
        if collection.count() == 0:
            logger.warning(f"Collection '{collection_name}' is empty")
            return []

        results = collection.query(
            query_texts=[query_text],
            n_results=min(n_results, collection.count()),
        )

        hits = []
        for i in range(len(results["documents"][0])):
            hits.append({
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return hits

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        words = text.split()
        chunks = []
        step = config.CHUNK_SIZE - config.CHUNK_OVERLAP
        for start in range(0, len(words), step):
            chunk = " ".join(words[start : start + config.CHUNK_SIZE])
            if chunk.strip():
                chunks.append(chunk)
        return chunks if chunks else [text]

    def list_collections(self) -> list[str]:
        """List all collection names."""
        return [c.name for c in self.client.list_collections()]

    def collection_count(self, name: str) -> int:
        """Get document count in a collection."""
        try:
            return self.get_or_create_collection(name).count()
        except Exception:
            return 0


# ── Singleton ──────────────────────────────────────────────────────────
_store: Optional[VectorStore] = None


def get_vectorstore() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
