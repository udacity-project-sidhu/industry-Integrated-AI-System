"""Ingestion + retrieval orchestration for the RAG knowledge base.

Use `ingest()` to (re)build the Chroma collection from `knowledge_base/`.
Use `search()` for top-k retrieval at agent runtime.
"""
from __future__ import annotations

from ..config import settings
from .knowledge_base import chunk_markdown, load_knowledge_base
from .manifest import changed_files, save_manifest
from .vector_store import add_chunks, count, query, remove_by_source


def ingest(force: bool = False) -> dict:
    """Embed and upsert any changed markdown files into Chroma.

    Returns a small summary dict so callers / tests can verify behaviour.
    """
    kb_dir = settings.knowledge_base_dir
    if force:
        # Wipe and re-ingest everything
        for md_path in sorted(kb_dir.glob("*.md")):
            remove_by_source(md_path.name)
        chunks = load_knowledge_base(kb_dir)
        added = add_chunks(chunks)
        # Rebuild manifest
        _, updated = changed_files(kb_dir)
        save_manifest(updated)
        return {"changed_files": [p.name for p in sorted(kb_dir.glob('*.md'))], "chunks_added": added, "total_chunks": count()}

    changed_paths, updated_manifest = changed_files(kb_dir)
    added = 0
    for path in changed_paths:
        remove_by_source(path.name)
        chunks = chunk_markdown(path.read_text(encoding="utf-8"), path.name)
        added += add_chunks(chunks)
    save_manifest(updated_manifest)
    return {
        "changed_files": [p.name for p in changed_paths],
        "chunks_added": added,
        "total_chunks": count(),
    }


def search(text: str, k: int = 4):
    return query(text, k=k)
