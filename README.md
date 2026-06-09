# The Unofficial Guide — Project 1: Skateboarding RAG

A retrieval-augmented generation (RAG) system that answers skateboarding
questions using **only** a corpus of 10 collected skateboarding documents —
and refuses when the documents don't cover the question.

**Pipeline:** Document Ingestion → Chunking → Embedding + Vector Store →
Retrieval → Grounded Generation → Web UI.

### Run it

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# add your free Groq key (https://console.groq.com) to .env:
copy .env.example .env        # then edit GROQ_API_KEY

python src\ingest.py          # scrape + clean -> documents/*.txt
python src\embed.py           # embed chunks -> chroma_db/
python app.py                 # web UI at http://localhost:7860
```

`demo_questions.txt` contains 20 ready-to-use demo questions.

---

## Domain

This system covers **skateboarding best practices for beginners** — how to
start riding, choose equipment, stay safe, learn first tricks, maintain a
board, and behave at a skatepark.

This knowledge is valuable but hard to find through official channels because
skateboarding has no single authoritative manual. The real, practical
knowledge — what board size actually suits a beginner, which trick to learn
first, the unwritten rules of a skatepark — is spread across enthusiast blogs,
shop guides, community forums, and word-of-mouth. A RAG system is a good fit
because it can synthesize this scattered, experience-based knowledge into
direct answers while still pointing back to the source.

---

## Document Sources

| #  | Source | Type | URL |
|----|--------|------|-----|
| 1  | SkateboardGeek — Skateboarding Tricks Guide | Trick guide | https://skateboardgeek.com/skateboarding-tricks/ |
| 2  | Skateboard GB — Learn to Skate Guide | Beginner guide (community org) | https://skateboardgb.org/beginners/learn-to-skate-guide/ |
| 3  | Skateboard Session — Grip Tape Maintenance | Maintenance how-to | https://skateboardsession.com/maintenance-repairs/skateboard-grip-tape-maintenance/ |
| 4  | Surfertoday — Beginner's Guide to Skateboarding | Fundamentals tutorial | https://www.surfertoday.com/skateboarding/the-beginners-guide-to-skateboarding |
| 5  | Surfertoday — The Story of Thrasher | Culture / history feature | https://www.surfertoday.com/skateboarding/thrasher-the-story-of-the-ultimate-skateboard-magazine |
| 6  | Skateboard Session — Skatepark Etiquette | Etiquette guide | https://skateboardsession.com/culture-and-community/skate-park-etiquette/ |
| 7  | Skate Avenue — Skateboard Size Guide | Sizing guide | https://skate-avenue.com/blogs/articles/skateboard-size-guide |
| 8  | Tactics — Skateboarding Safety & Gear Guide | Safety guide | https://www.tactics.com/info/skateboarding-safety-gear-guide |
| 9  | Tactics — How to Kickflip | Trick tutorial | https://www.tactics.com/info/how-to-kickflip |
| 10 | Retrospec — How to Skateboard: 5 Steps for Beginners | Beginner guide | https://retrospec.com/blogs/gear-guides/how-to-skateboard-5-steps-for-beginners |

Together these span tricks, riding fundamentals, equipment sizing, safety
gear, maintenance, skatepark etiquette, and skate culture — different
subtopics and perspectives within the domain. Three originally-planned
sources were swapped during ingestion (see Spec Reflection).

---

## Chunking Strategy

**Chunk size:** 500 characters

**Overlap:** 75 characters

**Why these choices fit the documents:** The documents are long-form
instructional guides (~2,800–18,000 characters each), not short reviews. In
this kind of text a single idea — one trick step, one safety rule, one sizing
recommendation — typically spans 2–3 sentences (~300–500 characters). A
500-character chunk is large enough to hold a complete instruction rather than
a fragment, but small enough to keep retrieval matches tight and specific. The
75-character overlap (~one sentence) guards against the biggest risk with
prose guides: a key instruction being split across a chunk boundary. I tested
larger chunks (800/100) during Milestone 4 and they *degraded* my best query
(deck sizing), so I kept 500/75.

**Preprocessing before chunking:** HTML was stripped to article text with
BeautifulSoup (removing `<script>`, `<nav>`, `<header>`, `<footer>`, `<aside>`,
etc.), the `<article>`/`<main>` container with the most text was selected to
avoid teaser-card noise, paragraph/list blocks shorter than 25 characters were
dropped (tuned empirically — removes nav links and split table cells while
keeping the size-chart lines), and cookie/newsletter boilerplate was filtered
by phrase. Chunk boundaries snap to whitespace so words are never split
mid-token.

**Final chunk count:** 259 chunks across 10 documents.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dimension
embeddings). It runs locally with no API key, no cost, and no rate limits, and
performs well on general English instructional text. Chunks are stored in a
persistent ChromaDB collection using **cosine distance**, and queries are
embedded with the same model so query and chunk vectors are comparable.

**Production tradeoff reflection:** If I were deploying this for real users and
cost weren't a constraint, the biggest factor I'd weigh is **accuracy on
domain-specific text**. MiniLM is trained on general English and treats skate
slang (*ollie, goofy, pop shuvit, grip gum*) as ordinary tokens; a larger or
domain-tuned model (e.g. OpenAI `text-embedding-3-large`) might match
jargon-heavy queries better — this is directly relevant to my Q1/Q2 retrieval
misses below. I'd also weigh **context length** (MiniLM only reads ~256 tokens,
fine for my 500-char chunks but limiting if I wanted bigger ones) and
**local-vs-hosted cost/privacy** (MiniLM is free and private; a hosted model
adds a per-query network call and sends user queries to a third party). For a
free community tool, the local MiniLM model is the right call; for a paid
product I'd prototype a hosted model and measure retrieval accuracy on
skate-specific queries before switching.

---

## Grounded Generation

**System prompt grounding instruction:** The LLM (Groq
`llama-3.3-70b-versatile`, `temperature=0`) receives a strict system prompt:

> *"Answer the user's question using ONLY the numbered context documents
> provided. Use only facts found in the context. Do NOT use outside or prior
> knowledge. If the context does not contain enough information to answer,
> reply with exactly: 'I don't have enough information on that.' Do not guess,
> infer beyond the text, or add general skateboarding knowledge. Cite the
> source name(s) you used in parentheses."*

Grounding is enforced structurally, not just suggested: the retrieved chunks
are the *only* knowledge passed to the model, each chunk is numbered and
labeled with its source name, `temperature=0` keeps output context-faithful,
and the explicit refusal sentence gives the model a defined "I don't know"
path instead of inventing an answer (verified on Q4 below).

**How source attribution is surfaced in the response:** Two layers. (1) The
model cites source names inline, e.g. *"(Source: Skate Avenue — Skateboard Size
Guide)"*. (2) More importantly, the `sources` list shown in the UI under
"Retrieved from" is built **programmatically in code** from the retrieved
chunks' metadata (source name + URL) — it does not depend on the LLM. If the
model refuses for lack of information, the source list is intentionally empty.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What basic skills should a beginner master before trying tricks? | Stance, pushing, turning, stopping (foot braking) | Reported the docs don't explicitly list the basics; mentioned only the ollie-prep motion | Partially relevant | Partially accurate |
| 2 | What trick should a beginner learn first, and why? | The ollie (foundation for other tricks) | Correctly answered "the Ollie first," citing two guides | Partially relevant | Accurate |
| 3 | What deck width and length should a beginner look for, and why? | ~8.0"–8.25" width; ~31–32" (range 28–33") length; stability | 8.0"–8.25" width, 28"–33" length, for stability/control | Relevant | Accurate |
| 4 | Where are the best skateparks near me to learn at? | (Out-of-scope) System should refuse — no location data | "I don't have enough information on that." | Off-target by design (no location data exists) | Accurate (correct refusal) |
| 5 | What safety gear should a beginner wear, and why? | Helmet, knee/elbow pads, wrist guards, proper shoes | Helmet, knee pads, elbow pads, wrist guards; builds confidence | Relevant | Accurate |

**Retrieval quality:** Relevant (Q3, Q5), Partially relevant (Q1, Q2),
Off-target by design (Q4).
**Response accuracy:** Accurate (Q2, Q3, Q4, Q5), Partially accurate (Q1).

---

## Failure Case Analysis

**Question that failed:** *"What basic skills should a beginner master before
trying tricks?"* (Q1)

**What the system returned:** *"The context documents do not explicitly state
the basic skills a beginner should master before trying tricks… However, it is
mentioned that getting familiar with the motion of popping up the board… is
important for learning the Ollie."* — i.e. a hedged, incomplete answer that
missed the expected fundamentals (stance, pushing, turning, stopping).

**Root cause (tied to a specific pipeline stage — retrieval/embedding):** The
expected content *does exist* in the corpus — the Surfertoday beginner guide,
Skateboard GB, and Retrospec all describe pushing, turning, and foot-braking.
But those instructions live in chunks framed around *riding*, while the query
phrase "basic skills… before trying **tricks**" embeds semantically closest to
the *trick-guide* introductions (SkateboardGeek, which literally opens "tips on
learning skateboarding tricks… from beginner to pro"). So the top-6 retrieved
chunks were trick-guide intros and etiquette text, not the push/turn/stop
sections. The fundamentals are also **spread across several documents** rather
than concentrated in one "basic skills" chunk, so no single chunk scored high.
With the right context absent, the grounding prompt did its job correctly and
the model declined to fabricate — a *correct* grounding behavior producing an
*incomplete* answer.

**What I would change to fix it:** (1) Add a source that explicitly lists
beginner fundamentals as a checklist so the concept lives in one high-signal
chunk. (2) Try a query-expansion step that rewrites "basic skills before
tricks" into terms the corpus uses ("pushing, turning, stopping, stance").
(3) Evaluate a domain-aware embedding model that better connects "basic skills"
with "how to ride." Notably, **Q2 had the same retrieval weakness but the LLM
recovered** — synthesizing "the ollie is first" from partial context — which
shows the failure is specifically about retrieval surfacing scattered,
oddly-phrased content, not about generation.

---

## Spec Reflection

**One way the spec helped me during implementation:** Writing the Chunking
Strategy, Retrieval Approach, and architecture diagram in `planning.md` *first*
meant I had concrete parameters (500/75, `all-MiniLM-L6-v2`, top-k = 6) and a
clear build-time-vs-query-time split to hand directly to the implementation.
The code fell naturally into `ingest.py` → `chunk.py` → `embed.py` →
`retrieve.py` → `generate.py`, matching the diagram stage-for-stage, with very
little rework — because the decisions were already made and justified.

**One way my implementation diverged from the spec, and why:** Several
document sources and one evaluation question changed once I hit reality.
During ingestion, two planned sources (skateboarding.com tutorials) returned
HTTP 403 to scrapers even with a browser User-Agent, and one (ScopsLife) was
JavaScript-rendered so only its intro extracted — so I swapped in scrapeable
equivalents (Surfertoday, Tactics, Skateboard Session). And after retrieval
testing in Milestone 4, I discovered my original Q5 ("most common beginner
mistake") was barely covered by the corpus — the word "mistake" appeared once,
in an unrelated grip-tape context — so I reframed it to "What safety gear
should a beginner wear?", which the corpus covers well. I updated `planning.md`
to match. The lesson: a spec written before contact with real, messy web
sources has to flex when those sources don't behave as assumed.

---

## AI Usage

**Instance 1 — Ingestion & chunking code (`ingest.py`, `chunk.py`)**

- *What I gave the AI:* My `planning.md` Documents and Chunking Strategy
  sections (the 10 source URLs, chunk size 500, overlap 75) and asked it to
  write a scraper that cleans HTML to article text plus a `chunk_text()`
  function matching my spec.
- *What it produced:* A working `requests` + BeautifulSoup scraper and a
  character-window chunker.
- *What I changed or overrode:* After inspecting the output I directed several
  fixes: word-boundary snapping so chunks don't cut mid-word; an empirically
  tuned minimum-block-length filter (I had it build an inspection tool, then
  chose 25 chars from the data); manifest-driven chunking so stale `.txt`
  files can't silently pollute the corpus; and saving raw HTML *before*
  cleaning. I also re-ran ingestion and replaced three sources when they 403'd
  or were JS-rendered.

**Instance 2 — Embedding, retrieval & grounded generation (`embed.py`,
`retrieve.py`, `generate.py`)**

- *What I gave the AI:* My Retrieval Approach section and the grounding
  requirement (answer from retrieved context only, with source attribution),
  and asked it to embed chunks into ChromaDB and write retrieval + generation.
- *What it produced:* `embed.py`/`retrieve.py`/`generate.py` with a top-k
  retrieval function and a Groq call.
- *What I changed or overrode:* I had it use **cosine** distance so scores
  were interpretable; when it suggested raising k to 8 to capture a missing
  chunk, I tested it, found the target chunk actually ranked ~15th, and
  **kept k = 6** instead. I used the retrieval test results to reframe Q5
  (corpus gap), and I verified the grounding refusal works on an out-of-scope
  question rather than trusting that the prompt alone would enforce it.

---

## Demo Video

A 3–5 minute walkthrough covering: 3+ queries with visible source citations,
one fully-working query (deck sizing), one failure/refusal case narrated
(skateparks near me → refusal; or Q1 → incomplete), and a walk through this
evaluation report.