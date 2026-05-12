"""Phase J - evaluation utilities.

Aggregate metrics, slice tables, RAG faithfulness, and failure-case enumeration
across both the ML and DL components and the GenAI explanation layer.

Lineage:
- Aggregate + slice metrics: P3 (ML), P4 (DL disaggregated evaluation discipline).
- RAG faithfulness check: P6 (evaluator-critic philosophy applied offline).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)


CITATION_RE = re.compile(r"\[S(\d+)\]")


@dataclass(frozen=True)
class AggregateMetrics:
    n: int
    positive_rate: float
    roc_auc: float
    pr_auc: float
    brier: float
    accuracy_at_0_5: float


def aggregate_metrics(probs: np.ndarray, y: pd.Series) -> AggregateMetrics:
    probs = np.asarray(probs)
    y_arr = np.asarray(y)
    return AggregateMetrics(
        n=int(len(y_arr)),
        positive_rate=float(y_arr.mean()),
        roc_auc=float(roc_auc_score(y_arr, probs)),
        pr_auc=float(average_precision_score(y_arr, probs)),
        brier=float(brier_score_loss(y_arr, probs)),
        accuracy_at_0_5=float(((probs >= 0.5).astype(int) == y_arr).mean()),
    )


def slice_table(
    probs: np.ndarray,
    y: pd.Series,
    slice_series: pd.Series,
    label: str,
) -> pd.DataFrame:
    """Per-group n, positive rate, ROC-AUC, Brier."""
    df = pd.DataFrame({"prob": np.asarray(probs), "y": np.asarray(y), "g": slice_series.values})
    rows = []
    for value, sub in df.groupby("g"):
        if sub["y"].nunique() < 2 or len(sub) < 10:
            auc = float("nan")
        else:
            auc = float(roc_auc_score(sub["y"], sub["prob"]))
        rows.append(
            {
                label: value,
                "n": int(len(sub)),
                "positive_rate": float(sub["y"].mean()),
                "roc_auc": auc,
                "brier": float(brier_score_loss(sub["y"], sub["prob"])) if len(sub) >= 1 else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def age_bucket(age: float) -> str:
    if age < 45:
        return "<45"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    return ">=65"


def failure_cases(
    X: pd.DataFrame, y: pd.Series, probs: np.ndarray, k: int = 5
) -> pd.DataFrame:
    """Top-k highest-confidence wrong predictions (calibration smell)."""
    df = X.copy()
    df["y_true"] = y.values
    df["prob"] = np.asarray(probs)
    df["pred"] = (df["prob"] >= 0.5).astype(int)
    wrong = df[df["pred"] != df["y_true"]].copy()
    wrong["confidence"] = (wrong["prob"] - 0.5).abs()
    return wrong.sort_values("confidence", ascending=False).head(k)


@dataclass(frozen=True)
class FaithfulnessReport:
    n_citations: int
    n_unique_citations: int
    n_chunks_available: int
    invalid_citation_indices: list[int]
    cited_indices: list[int]
    uncited_chunks_count: int
    explanation_token_overlap: float


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text)}


def rag_faithfulness(explanation_text: str, retrieved_chunks: Iterable) -> FaithfulnessReport:
    """Check that the explanation only cites available evidence and shares vocabulary with it.

    `retrieved_chunks` is an iterable of objects exposing a `.text` attribute
    (RetrievedChunk-style). Citation indices in the explanation are 1-based [S1]..[Sk].
    """
    chunks = list(retrieved_chunks)
    n_avail = len(chunks)

    raw = [int(m) for m in CITATION_RE.findall(explanation_text)]
    invalid = sorted({i for i in raw if i < 1 or i > n_avail})
    cited = sorted({i for i in raw if 1 <= i <= n_avail})

    expl_tokens = _tokens(explanation_text)
    cited_tokens: set[str] = set()
    for i in cited:
        cited_tokens |= _tokens(chunks[i - 1].text)
    overlap = (
        len(expl_tokens & cited_tokens) / len(expl_tokens) if expl_tokens else 0.0
    )

    return FaithfulnessReport(
        n_citations=len(raw),
        n_unique_citations=len(set(raw)),
        n_chunks_available=n_avail,
        invalid_citation_indices=invalid,
        cited_indices=cited,
        uncited_chunks_count=n_avail - len(cited),
        explanation_token_overlap=float(overlap),
    )
