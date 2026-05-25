r"""Smoke tests for the ML risk model.

cd 'C:\Users\dev\sources\udacity\Project 7 - Industry-integrated AI System\Intgerated AI Systems'

python -m pytest tests/test_ml_model.py

python -m pytest tests/test_ml_model.py -s

# or more verbose:
python -m pytest tests/test_ml_model.py -s -v

--------------------------------------------------------------------------------
see notes at the bottom of this file about what this function does.

"""
from __future__ import annotations

from src.data_loader import load_heart_disease
from src.ml_model import save, train_and_evaluate
from src.preprocessing import split_and_preprocess


def test_ml_model_trains_and_persists(tmp_path=None):
    df = load_heart_disease()
    split = split_and_preprocess(df)
    model, metrics = train_and_evaluate(split)
    assert 0.7 < metrics.cv_roc_auc_mean <= 1.0
    assert 0.7 < metrics.test_roc_auc <= 1.0
    path = save(model)
    assert path.exists()


"""
A smoke test for the classical ML risk model (ml_model.py — the scikit-learn HistGradientBoostingClassifier pipeline, sibling of the PyTorch net in test_dl_model.py).

One test: test_ml_model_trains_and_persists()
Three concerns in one shot:

Trains end-to-end — calls train_and_evaluate(split), which runs 5-fold stratified cross-validation on the training set and fits a final model on the full training set.

Performs better than a meaningful baseline — asserts:

0.7 < cv_roc_auc_mean ≤ 1.0 (cross-validated ROC-AUC),
0.7 < test_roc_auc ≤ 1.0 (held-out test ROC-AUC).
Note this is stricter than the DL test's > 0.5 ("better than random"). 0.7 is a real-quality bar — if a code or data change drops AUC below 0.7, the test fails loudly. This catches preprocessing bugs, label leakage regressions, hyperparameter tweaks gone wrong, etc.

Persists to disk — save(model) writes the pipeline to models/ml_model.joblib and the test asserts the file exists. Because the sklearn Pipeline bundles the preprocessor with the classifier, no separate input_dim is needed (unlike the DL test).

Why the AUC bar differs from the DL test
ML test: 0.7 < AUC — full CV, real training budget, expected to be solid.
DL test: 0.5 < AUC — only 10 epochs for speed, so just "learned something" is enough.
The tmp_path=None signature
That's just a leftover parameter; the test doesn't actually use pytest's tmp_path fixture. It writes to the real models/ml_model.joblib (the path defined in MODEL_PATH), so this run will overwrite whatever model file is already there.

What it does NOT test
PR-AUC or Brier (calibration) — computed by train_and_evaluate, but not asserted here.
Per-slice / fairness metrics (slice_metrics) — that lives in evaluation.py and is exercised in test_evaluation.py.
Reload-and-predict (saves, but doesn't load back and run inference).
Integration with the ensemble or orchestrator.
Cost / time
Offline, no API key. Slower than the data-pipeline tests (real CV + fit), faster than the DL test (sklearn HistGBM is much quicker than training a PyTorch net).

What this guards
The single most consequential test for the classical model: if anyone breaks preprocessing, swaps in a broken classifier, or accidentally introduces target leakage that reduces performance, the AUC floor here will catch it before downstream tests (decision layer, orchestrator) fail in confusing ways.


"""