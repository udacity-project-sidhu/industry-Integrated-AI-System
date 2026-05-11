"""Smoke test for the RAG layer.

Hits the live OpenAI API once for embeddings.
Skipped automatically if OPENAI_API_KEY is not set.
"""
from __future__ import annotations

from src.config import settings
from src.rag.knowledge_base import chunk_markdown, load_knowledge_base
from src.rag.retriever import ingest, search


def test_chunking_is_header_aware():
    text = "# Heading A\n\nbody A\n\n## Heading B\n\nbody B"
    chunks = chunk_markdown(text, "fake.md")
    assert len(chunks) == 2
    headings = {c.heading for c in chunks}
    assert "Heading A" in headings
    assert "Heading B" in headings


def test_load_knowledge_base_returns_chunks():
    chunks = load_knowledge_base()
    assert len(chunks) > 0
    sources = {c.source for c in chunks}
    assert any(s.endswith(".md") for s in sources)


def test_rag_end_to_end():
    if not settings.openai_api_key or settings.openai_api_key.startswith("PUT_YOUR"):
        print("skipping live API test - OPENAI_API_KEY not set")
        return
    summary = ingest()
    print("ingest summary:", summary)
    results = search("What does chest pain type 1 mean?", k=3)
    assert len(results) > 0
    top = results[0]
    print("top source:", top.source, "heading:", top.heading, "sim:", round(top.similarity, 3))
    assert top.similarity > 0.3
