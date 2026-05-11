"""Smoke test for the decision/ensemble layer."""
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
