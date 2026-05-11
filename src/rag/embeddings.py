"""OpenAI embeddings wrapper.

Lineage: pattern of `text-embedding-3-small` with simple batching is
adapted from Project 6 (Research Brief Agent). Implementation here is a
fresh, minimal wrapper around the current OpenAI Python SDK.
"""
from __future__ import annotations

from openai import OpenAI

from ..config import settings

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    if not texts:
        return []
    client = _get_client()
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = client.embeddings.create(model=settings.embedding_model, input=batch)
        out.extend(item.embedding for item in resp.data)
    return out
