"""Smoke tests for data loading and preprocessing."""
from __future__ import annotations

from src.data_loader import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    TARGET_COL,
    load_heart_disease,
)
from src.preprocessing import split_and_preprocess


def test_load_heart_disease_shape_and_target():
    df = load_heart_disease()
    assert len(df) > 0
    assert TARGET_COL in df.columns
    assert set(df[TARGET_COL].unique()).issubset({0, 1})
    for col in NUMERIC_FEATURES + CATEGORICAL_FEATURES:
        assert col in df.columns


def test_split_and_preprocess_runs():
    df = load_heart_disease()
    split = split_and_preprocess(df)
    assert len(split.X_train) > 0
    assert len(split.X_test) > 0
    assert len(split.X_train) + len(split.X_test) == len(df)
    transformed = split.preprocessor.transform(split.X_train)
    assert transformed.shape[0] == len(split.X_train)
    assert transformed.shape[1] >= len(NUMERIC_FEATURES)
