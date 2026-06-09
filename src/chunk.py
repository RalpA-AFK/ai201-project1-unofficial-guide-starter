"""Milestone 3 — Chunking.

Splits the ingested ``documents/*.txt`` files into overlapping chunks
ready for embedding (Milestone 4).

Chunking strategy (see planning.md):
    chunk size = 500 characters
    overlap    = 75 characters
A sliding window advances by ~(size - overlap) = ~425 chars, snapping to
whitespace so words are never split; the 75-char overlap means a sentence
on a boundary still appears whole in a neighbouring chunk.

Only files listed in ``documents/manifest.json`` are chunked, so stale or
experimental ``.txt`` files can't silently pollute the corpus.

Run from the repo root to see chunk stats and a sample:
    python src/chunk.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make stdout tolerant of non-ASCII on strict Windows consoles (Python 3.14).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = REPO_ROOT / "documents"
MANIFEST_PATH = DOCUMENTS_DIR / "manifest.json"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 75


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split ``text`` into overlapping chunks on word boundaries.

    Each chunk is at most ``chunk_size`` characters; consecutive chunks
    overlap by roughly ``overlap`` characters. Boundaries are snapped to
    whitespace so words are never split (the only exception is a single
    "word" longer than ``chunk_size``, which is hard-cut to guarantee
    progress).
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = text.strip()
    if not text:
        return []

    n = len(text)
    chunks: list[str] = []
    start = 0

    while start < n:
        end = min(start + chunk_size, n)

        # If we'd cut inside a word, back up to the last whitespace.
        if end < n and not text[end].isspace() and not text[end - 1].isspace():
            cut = max(text.rfind(" ", start, end), text.rfind("\n", start, end))
            if cut > start:
                end = cut

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break

        # Step back by `overlap`, then snap to the start of a whole word.
        nxt = end - overlap
        if nxt <= start:
            nxt = end  # pathological long word: guarantee forward progress
        else:
            space = text.rfind(" ", start, nxt)
            if space > start:
                nxt = space + 1
        start = nxt

    return chunks


def load_manifest() -> dict:
    """Load the manifest written by ingest.py (filename -> {url, name})."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"No manifest.json in {DOCUMENTS_DIR}. Run `python src/ingest.py` first."
        )
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def chunk_documents() -> list[dict]:
    """Chunk every document listed in the manifest.

    Returns a list of dicts, each with the chunk text plus metadata for
    source attribution downstream:
        {text, source_file, source_url, source_name, chunk_index}
    """
    manifest = load_manifest()

    # Warn about .txt files that aren't in the manifest — they are NOT chunked,
    # so stale/experimental files can't leak into the corpus. (To include a
    # manually added file, add it to manifest.json.)
    on_disk = {p.name for p in DOCUMENTS_DIR.glob("*.txt")}
    for name in sorted(on_disk - set(manifest)):
        print(f"  WARNING: {name} is not in manifest.json - skipping (not in corpus).")

    records: list[dict] = []
    for fname in sorted(manifest):
        path = DOCUMENTS_DIR / fname
        if not path.exists():
            print(f"  WARNING: {fname} is in manifest.json but the file is missing - skipping.")
            continue
        text = path.read_text(encoding="utf-8")
        meta = manifest[fname]
        for i, chunk in enumerate(chunk_text(text)):
            records.append({
                "text": chunk,
                "source_file": fname,
                "source_url": meta.get("url", ""),
                "source_name": meta.get("name", path.stem),
                "chunk_index": i,
            })

    return records


if __name__ == "__main__":
    records = chunk_documents()

    # Per-document breakdown
    per_file: dict[str, int] = {}
    for r in records:
        per_file[r["source_file"]] = per_file.get(r["source_file"], 0) + 1

    print(f"\nChunked {len(per_file)} documents into {len(records)} chunks "
          f"({CHUNK_SIZE} chars / {CHUNK_OVERLAP} overlap)\n")
    for name in sorted(per_file):
        print(f"  {per_file[name]:>4} chunks   {name}")

    print("\n--- sample chunk (first chunk of first doc) ---")
    print(repr(records[0]["text"]))
    print(f"\n(length: {len(records[0]['text'])} chars, "
          f"source: {records[0]['source_name']})")
