r"""Smoke test for the decision/ensemble layer.

cd 'C:\Users\dev\sources\udacity\Project 7 - Industry-integrated AI System\Intgerated AI Systems'

python -m pytest tests/test_decision.py

python -m pytest tests/test_decision.py -s

# or more verbose:
python -m pytest tests/test_decision.py -s -v

--------------------------------------------------------------------------------

A smoke test for the ensemble decision layer (decision.py), which sits between the two raw models (ML + DL) and the agent/explainer.

What the decision layer does
Ensembles the ML and DL probabilities into one ensemble_prob.
Maps that probability to a risk tier: low / moderate / high (threshold-based).
Flags confidence: high if the two models agree (within tolerance), low if they diverge — so a clinician knows when to distrust the ensemble.
What the test does
One test function: test_score_patient_and_cohort().

Loads & splits the Heart Disease data.
Trains both models from scratch:
ML pipeline (train_ml) → saved to disk.
DL net (train_dl, 10 epochs — short on purpose for speed) → saved with its input_dim.
score_patient — single-row path: takes one test patient, runs it through both models + the ensemble, and asserts:
ensemble_prob is a valid probability (0.0 ≤ p ≤ 1.0)
tier ∈ {low, moderate, high}
confidence ∈ {high, low}
score_cohort — batch path: scores the entire test set and asserts:
One row per input patient (no row loss).
All tier labels come from the allowed set.
What it does NOT test
Numerical correctness of the ensemble (just bounds and labels).
Threshold values themselves (low / moderate / high cutoffs).
The agreement tolerance for the confidence flag.
Calibration, accuracy, or model quality.
Any LLM / RAG / safeguards behavior.

What it does NOT test
Numerical correctness of the ensemble (just bounds and labels).
Threshold values themselves (low / moderate / high cutoffs).
The agreement tolerance for the confidence flag.
Calibration, accuracy, or model quality.
Any LLM / RAG / safeguards behavior.
Outputs
Pure pass/fail asserts — no prints, no log file. Just verifies the plumbing is wired so downstream code (the orchestrator, evaluation notebooks, scoring scripts) can rely on the decision API's shape and value ranges.

Cost / time
Offline but not cheap — it trains a fresh ML model and a 10-epoch DL model on every run. Takes seconds, not milliseconds. No OpenAI key needed.

"""
from __future__ import annotations

from src.data_loader import load_heart_disease
from src.decision import score_cohort, score_patient
from src.dl_model import save as save_dl, train_and_evaluate as train_dl
from src.ml_model import save as save_ml, train_and_evaluate as train_ml
from src.preprocessing import split_and_preprocess


def test_score_patient_and_cohort():
    df = load_heart_disease()
    split = split_and_preprocess(df)

    ml_pipeline, _ = train_ml(split)
    save_ml(ml_pipeline)
    dl_net, _ = train_dl(split, epochs=10)
    input_dim = split.preprocessor.transform(split.X_train).shape[1]
    save_dl(dl_net, input_dim=input_dim)

    one = split.X_test.iloc[[0]]
    s = score_patient(one, ml_pipeline, dl_net, split.preprocessor)
    assert 0.0 <= s.ensemble_prob <= 1.0
    assert s.tier in {"low", "moderate", "high"}
    assert s.confidence in {"high", "low"}

    cohort = score_cohort(split.X_test, ml_pipeline, dl_net, split.preprocessor)
    assert len(cohort) == len(split.X_test)
    assert set(cohort["tier"].unique()).issubset({"low", "moderate", "high"})
