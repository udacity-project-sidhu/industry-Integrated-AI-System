"""Smoke test for the DL risk model."""
from __future__ import annotations

from src.data_loader import load_heart_disease
from src.dl_model import save, train_and_evaluate
from src.preprocessing import split_and_preprocess


def test_dl_model_trains_and_persists():
    df = load_heart_disease()
    split = split_and_preprocess(df)
    model, metrics = train_and_evaluate(split, epochs=10)
    assert 0.5 < metrics.test_roc_auc <= 1.0
    input_dim = split.preprocessor.transform(split.X_train).shape[1]
    path = save(model, input_dim=input_dim)
    assert path.exists()
