"""Phase J smoke tests for src/evaluation.py."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.evaluation import (
    AggregateMetrics,
    age_bucket,
    aggregate_metrics,
    failure_cases,
    rag_faithfulness,
    slice_table,
)


class _FakeChunk:
    def __init__(self, text: str) -> None:
        self.text = text


def test_aggregate_metrics_basic() -> None:
    rng = np.random.default_rng(0)
    y = pd.Series(rng.integers(0, 2, 200))
    probs = (y * 0.6 + rng.uniform(0, 0.4, 200)).clip(0, 1)
    m = aggregate_metrics(probs, y)
    assert isinstance(m, AggregateMetrics)
    assert m.n == 200
    assert 0.5 < m.roc_auc <= 1.0
    assert 0.0 <= m.brier <= 1.0


def test_slice_table_returns_per_group() -> None:
    rng = np.random.default_rng(1)
    n = 120
    y = pd.Series(rng.integers(0, 2, n))
    probs = (y * 0.5 + rng.uniform(0, 0.5, n)).clip(0, 1)
    g = pd.Series(rng.choice(["a", "b", "c"], n))
    out = slice_table(probs, y, g, label="grp")
    assert set(out.columns) == {"grp", "n", "positive_rate", "roc_auc", "brier"}
    assert len(out) == 3


def test_age_bucket_boundaries() -> None:
    assert age_bucket(40) == "<45"
    assert age_bucket(45) == "45-54"
    assert age_bucket(54.9) == "45-54"
    assert age_bucket(55) == "55-64"
    assert age_bucket(64.9) == "55-64"
    assert age_bucket(65) == ">=65"


def test_failure_cases_returns_topk() -> None:
    df = pd.DataFrame({"f": range(10)})
    y = pd.Series([0, 0, 1, 1, 0, 1, 0, 1, 0, 1])
    probs = np.array([0.95, 0.10, 0.05, 0.99, 0.50, 0.50, 0.92, 0.05, 0.01, 0.95])
    out = failure_cases(df, y, probs, k=3)
    assert len(out) == 3
    # the highest-confidence-wrong should be at the top
    assert out.iloc[0]["confidence"] >= out.iloc[-1]["confidence"]


def test_rag_faithfulness_valid_and_invalid() -> None:
    chunks = [
        _FakeChunk("Hypertension is a major modifiable cardiovascular risk factor."),
        _FakeChunk("ST depression on exercise testing suggests inducible ischemia."),
    ]
    text = "Patient has hypertension [S1] with ST depression [S2]; also references [S5]."
    report = rag_faithfulness(text, chunks)
    assert report.n_chunks_available == 2
    assert report.cited_indices == [1, 2]
    assert report.invalid_citation_indices == [5]
    assert report.uncited_chunks_count == 0
    assert report.explanation_token_overlap > 0.0


if __name__ == "__main__":
    test_aggregate_metrics_basic()
    test_slice_table_returns_per_group()
    test_age_bucket_boundaries()
    test_failure_cases_returns_topk()
    test_rag_faithfulness_valid_and_invalid()
    print("ok")
