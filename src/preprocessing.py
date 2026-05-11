"""Preprocessing pipeline for the Heart Disease tabular task.

Lineage: the `log1p` + `StandardScaler` + scikit-learn `ColumnTransformer`
pattern is adapted from Project 3 (Machine Learning, UCI Online Retail II
K-Means RFM segmentation), reapplied here in a supervised setting with
one-hot encoding for categorical features.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from .data_loader import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    TARGET_COL,
    feature_columns,
)

RANDOM_STATE = 42


@dataclass
class SplitData:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    preprocessor: ColumnTransformer


def build_preprocessor() -> ColumnTransformer:
    log1p = FunctionTransformer(np.log1p, validate=False, feature_names_out="one-to-one")
    numeric_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("log1p", log1p),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, NUMERIC_FEATURES),
            ("cat", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )


def split_and_preprocess(
    df: pd.DataFrame, test_size: float = 0.2, random_state: int = RANDOM_STATE
) -> SplitData:
    X = df[feature_columns()].copy()
    y = df[TARGET_COL].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    preprocessor = build_preprocessor()
    preprocessor.fit(X_train)

    return SplitData(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        preprocessor=preprocessor,
    )
