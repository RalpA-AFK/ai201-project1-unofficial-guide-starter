"""Milestone 4 — Embedding + Vector Store.

Loads the chunks from the ingestion pipeline (chunk.py), embeds them with
all-MiniLM-L6-v2, and stores them in a persistent ChromaDB collection with
source metadata for attribution.

Cosine distance is used (``hnsw:space = cosine``) so distance scores are
comparable to the 0.0-1.0+ scale the rubric describes.

Run from the repo root (after ingest.py + chunk.py work):
    python src/embed.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from chunk import chunk_documents

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR = REPO_ROOT / "chroma_db"          # persistent store (gitignored)
COLLECTION_NAME = "skateboarding"
EMBED_MODEL = "all-MiniLM-L6-v2"


def build_index() -> None:
    """Embed every chunk and (re)build the ChromaDB collection from scratch."""
    records = chunk_documents()
    texts = [r["text"] for r in records]
    print(f"Embedding {len(texts)} chunks with {EMBED_MODEL} ...")

    model = SentenceTransformer(EMBED_MODEL)
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # Rebuild fresh each run so re-running never duplicates chunks.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:  # noqa: BLE001 - collection may not exist yet
        pass
    collection = client.create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    collection.add(
        ids=[f"{r['source_file']}::{r['chunk_index']}" for r in records],
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=[
            {
                "source_file": r["source_file"],
                "source_name": r["source_name"],
                "source_url": r["source_url"],
                "chunk_index": r["chunk_index"],
            }
            for r in records
        ],
    )

    print(f"Stored {collection.count()} chunks in ChromaDB at {CHROMA_DIR}")


if __name__ == "__main__":
    build_index()