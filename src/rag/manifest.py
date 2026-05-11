"""sha256 ingest manifest for idempotent re-ingestion.

Lineage: P6 (Research Brief Agent) used a sha256 manifest per source to
make re-ingestion a no-op for unchanged files. Implementation here is a
fresh, minimal version on top of `pathlib` + `hashlib` + JSON.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..config import settings

MANIFEST_PATH = settings.chroma_dir / "ingest_manifest.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_manifest() -> dict[str, str]:
    if not MANIFEST_PATH.exists():
        return {}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(manifest: dict[str, str]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def changed_files(kb_dir: Path) -> tuple[list[Path], dict[str, str]]:
    """Return (paths that changed since last ingest, updated manifest)."""
    manifest = load_manifest()
    updated = dict(manifest)
    changed: list[Path] = []
    for path in sorted(kb_dir.glob("*.md")):
        digest = _sha256_file(path)
        if manifest.get(path.name) != digest:
            changed.append(path)
            updated[path.name] = digest
    return changed, updated
