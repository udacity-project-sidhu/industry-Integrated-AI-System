"""Chroma vector store for the RAG knowledge base."""
from __future__ import annotations

from dataclasses import dataclass

import chromadb

from ..config import settings
from .embeddings import embed_texts
from .knowledge_base import Chunk

COLLECTION_NAME = "clinical_kb"


@dataclass
class RetrievedChunk:
    text: str
    source: str
    heading: str
    distance: float
    similarity: float  # 1 - distance for cosine


def get_collection():
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def add_chunks(chunks: list[Chunk]) -> int:
    if not chunks:
        return 0
    collection = get_collection()
    embeddings = embed_texts([c.text for c in chunks])
    collection.upsert(
        ids=[c.id for c in chunks],
        documents=[c.text for c in chunks],
        embeddings=embeddings,
        metadatas=[{"source": c.source, "heading": c.heading} for c in chunks],
    )
    return len(chunks)


def remove_by_source(source: str) -> int:
    collection = get_collection()
    result = collection.get(where={"source": source})
    ids = result.get("ids", [])
    if ids:
        collection.delete(ids=ids)
    return len(ids)


def query(text: str, k: int = 4) -> list[RetrievedChunk]:
    collection = get_collection()
    embedding = embed_texts([text])[0]
    res = collection.query(query_embeddings=[embedding], n_results=k)
    out: list[RetrievedChunk] = []
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        out.append(
            RetrievedChunk(
                text=doc,
                source=meta.get("source", "?"),
                heading=meta.get("heading", "?"),
                distance=float(dist),
                similarity=1.0 - float(dist),
            )
        )
    return out


def count() -> int:
    return get_collection().count()
