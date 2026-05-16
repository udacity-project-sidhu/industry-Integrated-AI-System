"""Central configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    # Evaluator runs on a different snapshot than the explainer so the
    # rubric judge cannot trivially rubber-stamp its own generations.
    evaluator_model: str = os.getenv("OPENAI_EVALUATOR_MODEL", "gpt-4o")
    embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    project_root: Path = PROJECT_ROOT
    data_raw: Path = PROJECT_ROOT / "data" / "raw"
    models_dir: Path = PROJECT_ROOT / "models"
    knowledge_base_dir: Path = PROJECT_ROOT / "knowledge_base"
    chroma_dir: Path = PROJECT_ROOT / "chroma_db"


settings = Settings()
