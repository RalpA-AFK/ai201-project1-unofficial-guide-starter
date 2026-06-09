"""Milestone 3 — Document Ingestion.

Scrapes each source in ``sources.py``, strips the HTML down to readable
article text, and saves one ``.txt`` file per source in ``documents/``.

Key detail (see planning.md): several of these sites return HTTP 403 to
bots, so requests are sent with a real browser ``User-Agent`` header.

Run from the repo root:
    python src/ingest.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from sources import SOURCES

# Windows consoles default to a strict cp1252 encoding on Python 3.14, so
# printing em dashes / curly quotes would crash with UnicodeEncodeError.
# Make stdout tolerant of any character.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

# documents/ lives at the repo root (this file is in src/)
REPO_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = REPO_ROOT / "documents"
RAW_DIR = REPO_ROOT / "raw_html"  # raw scraped HTML, saved before cleaning
MANIFEST_PATH = DOCUMENTS_DIR / "manifest.json"

# A browser User-Agent so sites that block bots (403) serve us real content.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 20  # seconds

# Tags that never contain article content — removed before extraction.
JUNK_TAGS = ["script", "style", "nav", "header", "footer", "aside",
             "form", "noscript", "button", "svg", "iframe"]
# Content-bearing tags we collect text from.
CONTENT_TAGS = ["h1", "h2", "h3", "h4", "p", "li"]
HEADING_TAGS = {"h1", "h2", "h3", "h4"}

# Minimum length for a paragraph/list block to be kept. Drops short
# navigation / "related links" / button noise. Headings are always kept
# (they are short by nature but give structure). Tuned empirically — see
# inspect_blocks.py.
MIN_BLOCK_LEN = 25

# Boilerplate a length filter can't catch (cookie banners, newsletter CTAs,
# nav links) — dropped if any phrase appears in the block (case-insensitive).
JUNK_PHRASES = (
    "manage options", "manage services", "manage {vendor", "manage vendor",
    "read more about these purposes", "sign up to receive", "subscribe to",
    "back to all", "view cart", "add to cart", "follow us",
)
# Leftover templating variables, e.g. "{title}", "{vendor_count}".
TEMPLATE_VAR_RE = re.compile(r"\{[a-z_]+\}")


def is_boilerplate(text: str) -> bool:
    """True if a block is cookie/nav/newsletter boilerplate to discard."""
    if TEMPLATE_VAR_RE.search(text):
        return True
    low = text.lower()
    return any(phrase in low for phrase in JUNK_PHRASES)


def fetch_html(url: str) -> str:
    """Download a page, raising on HTTP errors (incl. 403)."""
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def candidate_blocks(html: str) -> list[tuple[str, str]]:
    """Return ``(tag_name, text)`` for each content element in the main container.

    Picks the ``<article>``/``<main>`` container with the MOST text (so a page
    full of teaser-card ``<article>`` elements doesn't fool us into grabbing a
    sidebar snippet); falls back to ``<body>``. No length filtering here — that
    is applied in ``extract_main_text`` so it can be tuned/inspected separately.
    """
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(JUNK_TAGS):
        tag.decompose()

    containers = soup.find_all(["article", "main"])
    if containers:
        container = max(containers, key=lambda c: len(c.get_text(strip=True)))
    else:
        container = soup.body or soup

    blocks: list[tuple[str, str]] = []
    for element in container.find_all(CONTENT_TAGS):
        text = element.get_text(separator=" ", strip=True)
        if text:
            blocks.append((element.name, text))
    return blocks


def extract_main_text(html: str, min_block_len: int = MIN_BLOCK_LEN) -> str:
    """Strip HTML to clean, readable article text.

    Keeps every heading plus any paragraph/list item at least
    ``min_block_len`` characters long (filters short link/nav noise).
    """
    blocks = candidate_blocks(html)
    kept = [
        text for (tag, text) in blocks
        if (tag in HEADING_TAGS or len(text) >= min_block_len)
        and not is_boilerplate(text)
    ]

    # Fallback: non-semantic page with no usable blocks — take raw text.
    if not kept:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(JUNK_TAGS):
            tag.decompose()
        kept = [(soup.body or soup).get_text(separator="\n", strip=True)]

    text = "\n\n".join(kept)
    text = re.sub(r"[ \t]+", " ", text)        # collapse runs of spaces/tabs
    text = re.sub(r"\n{3,}", "\n\n", text)      # collapse blank-line runs
    return text.strip()


def ingest() -> None:
    """Scrape every source and write one .txt per source + a manifest.

    Raw HTML is saved to raw_html/ *before* cleaning, so the cleaning step
    (extract_main_text) can be re-run / re-tuned without re-scraping.
    """
    DOCUMENTS_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)
    manifest = {}
    successes, failures = 0, 0
    last_index = len(SOURCES) - 1

    for i, source in enumerate(SOURCES):
        label = f"[{source['id']:>2}] {source['name']}"
        try:
            html = fetch_html(source["url"])
            # Step 1: save the raw HTML before any cleaning.
            (RAW_DIR / f"{source['slug']}.html").write_text(html, encoding="utf-8")
            # Step 2: clean the raw HTML down to article text.
            text = extract_main_text(html)

            if len(text) < 200:
                # Too short almost always means a blocked/empty/JS-only page.
                raise ValueError(
                    f"extracted only {len(text)} chars - likely blocked or "
                    f"JavaScript-rendered"
                )

            out_path = DOCUMENTS_DIR / f"{source['slug']}.txt"
            out_path.write_text(text, encoding="utf-8")
            manifest[f"{source['slug']}.txt"] = {
                "url": source["url"],
                "name": source["name"],
            }
            successes += 1
            print(f"  OK   {label}  ->  {out_path.name}  ({len(text):,} chars)")

        except Exception as exc:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"  FAIL {label}\n         {type(exc).__name__}: {exc}")

        if i != last_index:
            time.sleep(1)  # be polite — don't hammer the servers

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nDone: {successes} succeeded, {failures} failed.")
    print(f"Text files + manifest.json written to {DOCUMENTS_DIR}")
    if failures:
        print(
            "\nSome sources failed. If it was a 403, the site blocks scrapers "
            "even with a browser User-Agent - open the page in a browser, copy "
            "the article text into documents/<slug>.txt manually, then add it to "
            "manifest.json (chunk.py only chunks files listed in the manifest)."
        )


if __name__ == "__main__":
    ingest()