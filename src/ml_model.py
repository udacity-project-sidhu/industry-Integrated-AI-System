"""Machine-learning risk model for the Heart Disease cohort.

Lineage: scikit-learn `Pipeline` + scaling discipline is adapted from
Project 3 (Machine Learning, UCI Online Retail II K-Means RFM(Recency, Frequency, Monetary) 
was a K-Means clustering on the UCI Online Retail II dataset, 
where customers were grouped using those three RFM features (which need scaling before K-Means). 
The current file borrows the Pipeline + scaler discipline from that work, but applies it to a 
fresh supervised binary classifier on tabular clinical features instead — no RFM features are used here.

"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline

from .config import settings
from .preprocessing import RANDOM_STATE, SplitData, build_preprocessor

MODEL_PATH = settings.models_dir / "ml_model.joblib"

# CV — Cross-Validation. Splits training data into folds, trains on some, evaluates on the held-out fold, rotates. 
#      cv_roc_auc_mean / cv_roc_auc_std are the average and spread across folds.

# K-Fold / Stratified K-Fold — CV scheme with K folds; stratified preserves the positive/negative class ratio in each fold.

# HistGradientBoostingClassifier — scikit-learn's Histogram-based Gradient Boosting classifier. 
#     Bins features into histograms for speed; an ensemble of boosted decision trees.

@dataclass
class MLMetrics:
    cv_roc_auc_mean: float  # mean cross-validated ROC-AUC(Receiver Operating Characteristic – Area Under the Curve) on the training set
    cv_roc_auc_std: float   # standard deviation of cross-validated ROC-AUC on the training set
    test_roc_auc: float     # ROC-AUC on the test set
    test_pr_auc: float      # Precision-Recall AUC on the test set
    test_brier: float       # Brier score on the test set. Mean squared error between predicted probabilities and actual 0/1 outcomes.


def build_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", build_preprocessor()),
            (
                "clf",
                HistGradientBoostingClassifier(
                    max_iter=300,
                    learning_rate=0.05,
                    max_depth=None,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )


def train_and_evaluate(split: SplitData, n_splits: int = 5) -> tuple[Pipeline, MLMetrics]:
    model = build_model()
    # creates a new, untrained sklearn Pipeline object and stores it in the variable `model`. 
    # The Pipeline consists of two steps: "preprocess", which applies the preprocessing transformations defined in 
    # `build_preprocessor()`, and "clf" - name given for classifier, which is a HistGradientBoostingClassifier with specified hyperparameters. 
    # This Pipeline will be trained on the training data and can be used to make predictions on new data, 
    # automatically applying the same preprocessing steps before classification.
    # HistGradientBoostingClassifier is a fast, scalable gradient boosting implementation that bins continuous 
    # features into histograms for efficiency.
   
    # https://www.geeksforgeeks.org/machine-learning/stratified-k-fold-cross-validation/
    # https://www.youtube.com/watch?v=fSytzGwwBVw&list=PLd58QvvY-imb5iwgg9vL04uwf7E-BsUmG
    # https://www.youtube.com/watch?v=BotYLBQfd5M&list=PLd58QvvY-imb5iwgg9vL04uwf7E-BsUmG&index=7
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    # split strategy for cross-validation. StratifiedKFold ensures that each fold has approximately the 
    # same percentage of samples of each target class as the complete set.
    
     # Cross-validation (CV) is a technique to evaluate model performance that uses the above split strategy 
     # to create multiple train/test splits from the training data.
    cv_scores = cross_val_score(
        model, split.X_train, split.y_train, scoring="roc_auc", cv=cv
    )
    # Returns an array of scores, one per fold. Each score is the ROC-AUC computed on the held-out fold after 
    # training on the other folds.

    # Learn from training inputs (X_train) and labels (y_train). 
    # HistGradientBoostingClassifier learns tree splits/leaf values to map features to disease probability.
    model.fit(split.X_train, split.y_train)

    # ROC-AUC, PR-AUC, and Brier are probability-based metrics.
    probs = model.predict_proba(split.X_test)[:, 1]

    # ROC-AUC alone:
    #   good for ranking, but says little about calibration.
    # PR-AUC:
    #   checks positive-class usefulness where false positives/precision matter.
    # Brier:
    #   checks whether probabilities are trustworthy, not just rank order.
    # CV mean/std:
    #   adds robustness context (performance level + volatility), helps catch unstable models and overfitting risk.

    metrics = MLMetrics(
        cv_roc_auc_mean=float(cv_scores.mean()),  # average ROC-AUC across CV folds on training data..
        cv_roc_auc_std=float(cv_scores.std()),    # standard deviation of fold ROC-AUC values.
        test_roc_auc=float(roc_auc_score(split.y_test, probs)), #final out-of-sample discrimination quality (how well positives are ranked above negatives)
        test_pr_auc=float(average_precision_score(split.y_test, probs)), # Precision-Recall AUC on test set, more sensitive to positive-class performance and useful under class imbalance; complements ROC-AUC.
        test_brier=float(brier_score_loss(split.y_test, probs)), # mean squared error of predicted probabilities vs true labels.
    )
    return model, metrics


def save(model: Pipeline, path: Path = MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    return path


def load(path: Path = MODEL_PATH) -> Pipeline:
    return joblib.load(path)


def predict_proba(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(X)[:, 1]


def slice_metrics(
    model: Pipeline, X: pd.DataFrame, y: pd.Series, slice_col: str
) -> pd.DataFrame:
    """Per-slice ROC-AUC + positive rate.

    Lineage: per-slice disaggregated evaluation is adapted from Project 4
    (Deep Learning, Fashion-MNIST CNN with dropout), where the headline
    accuracy hid large per-class differences. Here we apply the same
    discipline across clinical sub-cohorts (e.g. by sex or age band).
    """
    probs = predict_proba(model, X)
    rows = []
    for value, idx in X.groupby(slice_col).groups.items():
        idx = list(idx)
        y_slice = y.loc[idx]
        if y_slice.nunique() < 2 or len(y_slice) < 10:
            auc = float("nan")
        else:
            auc = float(roc_auc_score(y_slice, probs[X.index.get_indexer(idx)]))
        rows.append(
            {
                slice_col: value,
                "n": len(idx),
                "positive_rate": float(y_slice.mean()),
                "roc_auc": auc,
            }
        )
    return pd.DataFrame(rows)
