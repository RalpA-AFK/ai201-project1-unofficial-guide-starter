"""Milestone 5 — Grounded Generation.

Retrieves the top-k chunks, builds a prompt that forces the LLM to answer
ONLY from that context, calls Groq (llama-3.3-70b-versatile), and returns the
answer plus a programmatically-guaranteed list of the sources retrieved.

Grounding is enforced two ways:
  1. A strict system prompt: answer only from context, else refuse.
  2. temperature=0 for deterministic, context-faithful output.
Source attribution is NOT left to the LLM — the `sources` list is built in
code from the retrieved chunks' metadata.

Run from the repo root (needs GROQ_API_KEY in .env and a built index):
    python src/generate.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from retrieve import retrieve, DEFAULT_K

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

MODEL = "llama-3.3-70b-versatile"
REFUSAL = "I don't have enough information on that."

SYSTEM_PROMPT = (
    "You are a skateboarding assistant. Answer the user's question using ONLY "
    "the numbered context documents provided in the user message.\n\n"
    "Strict rules:\n"
    "- Use only facts found in the context. Do NOT use outside or prior "
    "knowledge.\n"
    f'- If the context does not contain enough information to answer, reply '
    f'with exactly: "{REFUSAL}" and nothing else.\n'
    "- Do not guess, infer beyond the text, or add general skateboarding "
    "knowledge.\n"
    "- Keep the answer concise (2-5 sentences) and specific to the context.\n"
    "- Cite the source name(s) you used in parentheses, e.g. (Source: <name>)."
)

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        key = os.getenv("GROQ_API_KEY", "")
        if not key or key.strip() in ("", "your_key_here"):
            raise RuntimeError(
                "GROQ_API_KEY is missing. Copy .env.example to .env and add your key."
            )
        _client = Groq(api_key=key)
    return _client


def _format_context(chunks: list[dict]) -> str:
    """Number each chunk and label it with its source so the LLM can cite it."""
    return "\n\n".join(
        f"[{i}] (Source: {c['source_name']})\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )


def ask(question: str, k: int = DEFAULT_K) -> dict:
    """Answer ``question`` grounded in the top-k retrieved chunks.

    Returns {answer, sources, chunks, refused}. ``sources`` is a code-built
    list of unique {name, url} from the retrieved chunks (empty if the model
    refused for lack of information).
    """
    chunks = retrieve(question, k)
    user_msg = (
        f"Context documents:\n\n{_format_context(chunks)}\n\n"
        f"Question: {question}"
    )

    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0,
    )
    answer = response.choices[0].message.content.strip()
    refused = answer.lower().startswith("i don't have enough information")

    # Source attribution guaranteed in code (unique, retrieval order).
    sources, seen = [], set()
    for c in chunks:
        key = (c["source_name"], c["source_url"])
        if key not in seen:
            seen.add(key)
            sources.append({"name": c["source_name"], "url": c["source_url"]})

    return {
        "answer": answer,
        "sources": [] if refused else sources,
        "chunks": chunks,
        "refused": refused,
    }


if __name__ == "__main__":
    demo_questions = [
        "What deck width and length should a beginner look for, and why?",
        "What safety gear should a beginner wear, and why?",
        "Where are the best skateparks near me to learn at?",  # out-of-scope
    ]
    for q in demo_questions:
        result = ask(q)
        print("=" * 80)
        print("Q:", q)
        print("-" * 80)
        print(result["answer"])
        if result["sources"]:
            print("\nRetrieved from:")
            for s in result["sources"]:
                print(f"  - {s['name']}  ({s['url']})")
        else:
            print("\n(no sources cited - system reported insufficient information)")
        print()