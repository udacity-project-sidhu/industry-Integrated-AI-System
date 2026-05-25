r"""Phase J smoke tests for src/evaluation.py.

cd 'C:\Users\dev\sources\udacity\Project 7 - Industry-integrated AI System\Intgerated AI Systems'

python -m pytest tests/test_evaluation.py

python -m pytest tests/test_evaluation.py -s

# or more verbose:
python -m pytest tests/test_evaluation.py -s -v

See notes at the bottom of this file about what this function does.
--------------------------------------------------------------------------------

"""
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


"""
Unit tests for evaluation.py — the offline evaluation toolkit used by notebooks 04/05 to report aggregate metrics, fairness slices, failure cases, and RAG faithfulness. Unlike the other test files, this one uses synthetic data, so it's fast, deterministic, and exercises the math directly.

Five tests
1. test_aggregate_metrics_basic — headline metrics
Generates synthetic labels + correlated probabilities (seeded RNG), runs aggregate_metrics, and asserts:

n matches input size,
roc_auc is better than chance (> 0.5),
brier is a valid probability score (0 ≤ brier ≤ 1).
Validates the AggregateMetrics dataclass returns coherent values.

2. test_slice_table_returns_per_group — fairness slices
Builds three random groups (a/b/c) and confirms slice_table:

Returns one row per group,
Has the expected columns: n, positive_rate, roc_auc, brier.
This is the per-cohort disaggregation used to detect hidden failures across subgroups (sex, age band, etc.).

3. test_age_bucket_boundaries — bucketing edge cases
Tests the age_bucket() helper at exact boundary values: <45 | 45–54 | 55–64 | ≥65. Catches off-by-one errors at the cutpoints — e.g. confirms 45 lands in 45-54 (not <45), and 65 lands in >=65.

4. test_failure_cases_returns_topk — highest-confidence wrongs
Feeds hand-crafted probs where some are very confidently wrong (e.g. 0.95 predicted but label is 0). Asserts:

Top-k length matches,
Results are sorted by confidence descending (the most embarrassing misses come first).
These are the rows you'd surface in a model card under "where the model fails badly" — a calibration smell.

5. test_rag_faithfulness_valid_and_invalid — citation grounding
Fakes two retrieved chunks and an explanation that cites [S1], [S2], and (deliberately) a non-existent [S5]. Asserts rag_faithfulness reports:

cited_indices == [1, 2] — what was referenced,
invalid_citation_indices == [5] — citation to a chunk that doesn't exist (hallucinated reference),
uncited_chunks_count == 0 — every retrieved chunk was used,
explanation_token_overlap > 0 — explanation vocabulary overlaps the evidence.
This is the offline counterpart to the LLM judge — a cheap, deterministic check that the explainer isn't fabricating citations.

What it does NOT test
Actual models, RAG ingestion, or LLM calls (no network, no API key).
Real-data metrics — only synthetic.
Cost / time
Milliseconds. Fully offline, deterministic (seeded), no models trained, no files written. The fastest test in the suite.

Why this matters
Notebook 04 (the evaluation notebook) leans on these functions to produce the model card numbers and the fairness/faithfulness tables. If any of these helpers silently break, your reported metrics become wrong — this file is the guardrail.


"""