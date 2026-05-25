r"""Smoke tests for data loading and preprocessing.

cd 'C:\Users\dev\sources\udacity\Project 7 - Industry-integrated AI System\Intgerated AI Systems'

python -m pytest tests/test_data_pipeline.py

python -m pytest tests/test_data_pipeline.py -s

# or more verbose:
python -m pytest tests/test_data_pipeline.py -s -v

--------------------------------------------------------------------------------
Two smoke tests for the data layer (the foundation before any model runs):

test_load_heart_disease_shape_and_target()
Validates data_loader.py:

Dataset loads and is non-empty.
Target column TARGET_COL exists.
Target is binary ({0, 1}) — i.e. the raw UCI multi-class severity (0–4) has been correctly collapsed 
to "disease / no disease".
All declared NUMERIC_FEATURES and CATEGORICAL_FEATURES are present (catches schema drift / typos 
/ renamed UCI columns).
test_split_and_preprocess_runs()
Validates preprocessing.py:

Both train and test splits are non-empty.
No rows lost or duplicated in the split (len(train) + len(test) == len(df)).
The fitted preprocessor can .transform() the training set, returns the same number of rows, 
and produces at least as many columns as numeric features (one-hot encoding of categoricals expands width, so >=).

What it deliberately does NOT test
The 80/20 ratio itself
Stratification correctness
Reproducibility (random_state)
Actual scaled/encoded values
Models, RAG, LLMs, safeguards
It's an integration smoke test — confirms the data → split → preprocess chain wires up correctly 
and produces sensibly-shaped outputs. Anything downstream (test_ml_model.py, test_dl_model.py, 
test_agent_orchestrator.py) implicitly assumes this passes.

It's also fast and offline — no API keys, no model training, no network beyond the first-time 
UCI fetch (cached to data/raw/heart_disease.csv).

"""
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
