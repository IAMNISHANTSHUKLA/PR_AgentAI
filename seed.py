"""Seed the ChromaDB vector store with coding standards and Confluence docs."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from vectorstore import get_vectorstore


def load_markdown_files(directory: Path) -> list[tuple[str, str]]:
    """Load all .md files from a directory. Returns list of (filename, content)."""
    files = []
    if directory.exists():
        for md_file in directory.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            files.append((md_file.stem, content))
    return files


def seed():
    """Seed all collections."""
    store = get_vectorstore()
    data_dir = Path(__file__).resolve().parent / "data"

    # ── Coding Standards ────────────────────────────────────────────────
    standards_dir = data_dir / "coding_standards"
    standards = load_markdown_files(standards_dir)

    if standards:
        store.add_documents(
            collection_name=config.COLLECTION_CODING_STANDARDS,
            documents=[content for _, content in standards],
            metadatas=[{"source": name, "type": "coding_standard"} for name, _ in standards],
            ids=[f"std_{name}" for name, _ in standards],
        )
        print(f"✅ Seeded {len(standards)} coding standards documents")
    else:
        print("⚠️  No coding standards found in data/coding_standards/")

    # ── Confluence Docs ─────────────────────────────────────────────────
    confluence_dir = data_dir / "confluence"
    confluence = load_markdown_files(confluence_dir)

    if confluence:
        store.add_documents(
            collection_name=config.COLLECTION_CONFLUENCE,
            documents=[content for _, content in confluence],
            metadatas=[{"source": name, "type": "confluence_doc"} for name, _ in confluence],
            ids=[f"conf_{name}" for name, _ in confluence],
        )
        print(f"✅ Seeded {len(confluence)} Confluence documents")
    else:
        print("⚠️  No Confluence docs found in data/confluence/")

    # ── Verify ──────────────────────────────────────────────────────────
    print(f"\n📊 Collections: {store.list_collections()}")
    for col_name in [config.COLLECTION_CODING_STANDARDS, config.COLLECTION_CONFLUENCE]:
        count = store.collection_count(col_name)
        print(f"   {col_name}: {count} chunks")

    print("\n🎉 Vector store seeded successfully!")


if __name__ == "__main__":
    seed()
