"""Dev tool — tune MIN_BLOCK_LEN for ingest.extract_main_text.

Fetches each source once (cached under .cache/html/), pulls the candidate
content blocks, and reports:
  1. a threshold table: how many non-heading blocks (and how much text) each
     MIN_BLOCK_LEN would drop across the whole corpus, and
  2. a dump of the short non-heading blocks so you can eyeball which are real
     content (keep) vs. nav/link noise (drop).

Run repeatedly while tuning — the HTML cache makes re-runs instant:
    python src/inspect_blocks.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from ingest import fetch_html, candidate_blocks, HEADING_TAGS
from sources import SOURCES

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

# Reuse the raw HTML that ingest.py saves (re-fetches only if missing).
CACHE_DIR = Path(__file__).resolve().parent.parent / "raw_html"
THRESHOLDS = [0, 10, 15, 20, 25, 30, 40, 50]
DUMP_UNDER = 50  # show non-heading blocks shorter than this


def get_html(source: dict) -> str:
    """Fetch HTML, caching to disk so re-runs don't hit the network."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{source['slug']}.html"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8", errors="replace")
    html = fetch_html(source["url"])
    cache_path.write_text(html, encoding="utf-8", errors="replace")
    return html


def main() -> None:
    blocks: list[tuple[int, str, str, str]] = []  # (id, name, tag, text)
    for source in SOURCES:
        try:
            html = get_html(source)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL [{source['id']}] {source['name']}: {exc}")
            continue
        for tag, text in candidate_blocks(html):
            blocks.append((source["id"], source["name"], tag, text))

    nonhead = [(i, n, tag, t) for (i, n, tag, t) in blocks
               if tag not in HEADING_TAGS]
    total_n = len(nonhead)
    total_chars = sum(len(t) for *_, t in nonhead)
    headings = len(blocks) - total_n

    print(f"\nCorpus: {len(blocks)} content blocks "
          f"({headings} headings always kept, {total_n} paragraph/list blocks)")
    print(f"Paragraph/list text total: {total_chars:,} chars\n")

    print("MIN_BLOCK_LEN impact on paragraph/list blocks (headings unaffected):")
    print(f"  {'thresh':>6} | {'dropped':>7} | {'kept':>5} | "
          f"{'chars dropped':>13} | {'% chars lost':>12}")
    print("  " + "-" * 56)
    for th in THRESHOLDS:
        kept = [t for *_, t in nonhead if len(t) >= th]
        dropped_n = total_n - len(kept)
        dropped_chars = total_chars - sum(len(t) for t in kept)
        pct = (dropped_chars / total_chars * 100) if total_chars else 0
        print(f"  {th:>6} | {dropped_n:>7} | {len(kept):>5} | "
              f"{dropped_chars:>13,} | {pct:>11.2f}%")

    print(f"\nShort paragraph/list blocks (< {DUMP_UNDER} chars) — keep or drop?")
    print(f"  {'len':>3} | {'tag':>3} | src | text")
    print("  " + "-" * 60)
    shorties = sorted((b for b in nonhead if len(b[3]) < DUMP_UNDER),
                      key=lambda b: len(b[3]))
    for src_id, _name, tag, text in shorties:
        print(f"  {len(text):>3} | {tag:>3} | {src_id:>2}  | {text}")
    if not shorties:
        print("  (none)")


if __name__ == "__main__":
    main()