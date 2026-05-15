"""Load and chunk markdown knowledge-base files.

Header-aware chunking: splits on top-level `#`/`##` headings so each chunk is
semantically coherent, then further splits any chunk longer than `max_chars`.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ..config import settings

HEADING_RE = re.compile(r"^#{1,3} ", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    source: str  # filename
    heading: str


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """Return [(heading, body), ...] from a markdown document."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_heading = "(preamble)"
    current_body: list[str] = []
    for line in lines:
        if HEADING_RE.match(line):
            if current_body:
                sections.append((current_heading, current_body))
            current_heading = line.strip("# ").strip()
            current_body = []
        else:
            current_body.append(line)
    if current_body:
        sections.append((current_heading, current_body))
    return [(h, "\n".join(body).strip()) for h, body in sections if "\n".join(body).strip()]


def _hard_split(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts = []
    paragraphs = re.split(r"\n\s*\n", text)
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) + 2 <= max_chars:
            buf = f"{buf}\n\n{para}".strip()
        else:
            if buf:
                parts.append(buf)
            buf = para
    if buf:
        parts.append(buf)
    return parts


def chunk_markdown(text: str, source: str, max_chars: int = 1500) -> list[Chunk]:
    # 1500 chars ~ 350-450 tokens: small enough to fit several chunks in the
    # LLM context window alongside the patient block, large enough to keep a
    # full guideline section intact in one chunk.
    chunks: list[Chunk] = []
    for heading, body in _split_by_headings(text):
        for piece in _hard_split(body, max_chars):
            chunk_text = f"# {heading}\n\n{piece}".strip()
            chunks.append(
                Chunk(
                    id=_sha256(f"{source}::{heading}::{piece}"),
                    text=chunk_text,
                    source=source,
                    heading=heading,
                )
            )
    return chunks


def load_knowledge_base(kb_dir: Path | None = None) -> list[Chunk]:
    kb_dir = kb_dir or settings.knowledge_base_dir
    chunks: list[Chunk] = []
    for md_path in sorted(kb_dir.glob("*.md")):
        chunks.extend(chunk_markdown(md_path.read_text(encoding="utf-8"), md_path.name))
    return chunks
