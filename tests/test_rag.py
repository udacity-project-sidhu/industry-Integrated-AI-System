r"""Smoke test for the RAG layer.

Hits the live OpenAI API once for embeddings.
Skipped automatically if OPENAI_API_KEY is not set.

cd 'C:\Users\dev\sources\udacity\Project 7 - Industry-integrated AI System\Intgerated AI Systems'

python -m pytest tests/test_rag.py

python -m pytest tests/test_rag.py -s

# or more verbose:
python -m pytest tests/test_rag.py -s -v

--------------------------------------------------------------------------------
see notes at the bottom of this file about what this function does.
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


"""
Smoke tests for the RAG (Retrieval-Augmented Generation) layer — the knowledge-base ingestion + vector-search subsystem under src/rag/ that feeds evidence chunks to the explainer.

Three tests: two offline (chunking + KB loading), one live (full embed + retrieve round-trip).

1. test_chunking_is_header_aware() — offline
Feeds a tiny synthetic Markdown string with two headings (# Heading A, ## Heading B) into chunk_markdown() and asserts:

It produces 2 chunks (one per heading),
Both heading names are preserved as chunk metadata.
This pins down the header-aware chunking contract: each Markdown section becomes its own retrievable chunk, with its heading attached. If someone "improves" the chunker into fixed-size windows that ignore document structure, this fails immediately. Heading metadata matters because the explainer uses it for human-readable citations.

2. test_load_knowledge_base_returns_chunks() — offline
Calls load_knowledge_base() (which reads every .md file under knowledge_base/) and asserts:

At least one chunk came back,
At least one source file ends in .md.
A wiring test — confirms the loader actually finds the knowledge_base/ directory and parses the real files (feature_dictionary.md, model_card.md, risk_factors.md, triage_workflow.md). Catches path bugs, empty directories, or wrong glob patterns.

3. test_rag_end_to_end() — live, only with OPENAI_API_KEY
The full retrieval pipeline against real OpenAI embeddings + Chroma:

ingest() — chunks the KB, embeds each chunk via the OpenAI embeddings API, upserts into the local Chroma store at chroma_db/. Idempotent (uses the manifest in ingest_manifest.json to skip re-embedding unchanged chunks — important so this test doesn't burn API tokens on every run).
search("What does chest pain type 1 mean?", k=3) — embeds the query, returns the top-3 most similar chunks by cosine similarity.
Asserts:
At least one result came back,
The top result's similarity > 0.3 (loose floor — guards against complete relevance collapse, e.g. embedding model mismatch, empty index, or wrong distance metric).
Prints the top chunk's source, heading, and similarity (visible with -s).
What it does NOT test
Exact ranking order (embeddings are deterministic but the floor is intentionally loose so KB edits don't constantly break the test).
The explainer's use of these chunks (that's test_genai_explainer.py).
Faithfulness / citation grounding (that's test_evaluation.py via rag_faithfulness).
Refusal on empty retrieval (that's test_genai_explainer.py).
Outputs
Chunking + KB loader: pure pass/fail.
End-to-end: prints ingest summary (counts of added/skipped chunks) and the top hit's metadata. Side effect: populates / updates chroma_db/ on disk.
Cost / time
Offline tests: milliseconds.
Live test: embeddings calls only (no chat completion) — cheap. First run after a KB change embeds everything; subsequent runs are near-free thanks to the ingest manifest.
What this isolates
The RAG layer's three contracts:

Chunking respects document structure (so citations make sense).
Loading finds the real KB files on disk.
Retrieval returns semantically relevant chunks for a real medical query — proving embeddings + vector store + similarity scoring all line up.
If RAG silently breaks, the explainer and orchestrator tests would still "pass" in a hollow way (refusal path, or LLM hallucination on garbage evidence). This test is what stops that.

"""