"""Milestone 4 — Retrieval.

Embeds a query with the same model used for the chunks and returns the
top-k most similar chunks from ChromaDB, with their source metadata and
cosine distance scores.

Run from the repo root (after embed.py has built the index) to test
retrieval against the evaluation questions from planning.md:
    python src/retrieve.py
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from embed import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

DEFAULT_K = 6          # planning.md Retrieval Approach: top-k = 6
WEAK_DISTANCE = 0.7    # cosine distance above this = weak match (rubric)

# 5 evaluation questions from planning.md (Q4 is the out-of-scope grounding test).
EVAL_QUESTIONS = [
    "What basic skills should a beginner master before trying tricks?",
    "What trick should a beginner learn first, and why?",
    "What deck width and length should a beginner look for, and why?",
    "Where are the best skateparks near me to learn at?",
    "What safety gear should a beginner wear, and why?",
]

_model: SentenceTransformer | None = None
_collection = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            _collection = client.get_collection(COLLECTION_NAME)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "ChromaDB collection not found. Run `python src/embed.py` first."
            ) from exc
    return _collection


def retrieve(query: str, k: int = DEFAULT_K) -> list[dict]:
    """Return the top-k chunks for ``query`` with source info + distance.

    Each result: {text, distance, source_file, source_name, source_url,
    chunk_index}, ordered closest first.
    """
    query_embedding = _get_model().encode([query]).tolist()
    res = _get_collection().query(
        query_embeddings=query_embedding,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    results = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        results.append({"text": doc, "distance": dist, **meta})
    return results


def _print_results(query: str, k: int = DEFAULT_K) -> None:
    print("=" * 80)
    print(f"QUERY: {query}")
    print("-" * 80)
    for rank, r in enumerate(retrieve(query, k), 1):
        flag = "   <-- WEAK (>0.7)" if r["distance"] > WEAK_DISTANCE else ""
        print(f"[{rank}] distance={r['distance']:.3f}  "
              f"{r['source_name']}  (chunk {r['chunk_index']}){flag}")
        snippet = " ".join(r["text"].split())[:200]
        print(textwrap.fill(snippet, width=78,
                            initial_indent="    ", subsequent_indent="    "))
    print()


if __name__ == "__main__":
    for q in EVAL_QUESTIONS:
        _print_results(q)