"""Smoke tests for the ML risk model."""
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
