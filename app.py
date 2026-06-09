"""Milestone 5 — Gradio web interface for the Unofficial Skateboarding Guide.

Run from the repo root:
    python app.py
then open http://localhost:7860
"""

import sys
from pathlib import Path

# Make the src/ modules importable when running `python app.py` from the root.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import gradio as gr  # noqa: E402

from generate import ask  # noqa: E402


def handle_query(question: str):
    """Run a question through the RAG pipeline and format answer + sources."""
    if not question or not question.strip():
        return "Please enter a question.", ""
    result = ask(question)
    if result["sources"]:
        sources = "\n".join(
            f"• {s['name']}\n  {s['url']}" for s in result["sources"]
        )
    else:
        sources = "(no sources — the system did not have enough information)"
    return result["answer"], sources


with gr.Blocks(title="The Unofficial Skateboarding Guide") as demo:
    gr.Markdown(
        "# 🛹 The Unofficial Skateboarding Guide\n"
        "Ask a skateboarding question. Answers come **only** from the collected "
        "documents — if the answer isn't in them, the system will say so."
    )
    inp = gr.Textbox(
        label="Your question",
        placeholder="e.g. What safety gear should a beginner wear?",
    )
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=5)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])


if __name__ == "__main__":
    demo.launch()