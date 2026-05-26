"""Ensemble + risk-tier decision layer.

Combines two model scores into one decision payload. 
It runs the gradient-boosting (ml_model) and PyTorch MLP (dl_model) scorers on a patient, 
then computes a weighted-average ensemble_prob (default 50/50).

Assigns a risk tier. _tier() buckets the ensemble probability into low (<0.30), 
moderate (0.30–0.70), or high (≥0.70). The wide moderate band is intentional — borderline patients 
get routed to human review.

Flags confidence based on model agreement. If |ml_prob − dl_prob| ≤ 0.20, confidence is "high"; 
otherwise "low". This is what lets the downstream agent surface "the two models disagree" to the clinician.

Returns all three probabilities, not just the ensemble. The PatientScore dataclass 
carries ml_prob, dl_prob, ensemble_prob, tier, confidence, and the thresholds used — 
so the LLM explainer cites the actual numbers and the decision stays auditable.


Lineage: P3 — "report cohort sizes alongside the metric" discipline,
applied here as "report all component scores alongside the ensemble".
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd

from . import dl_model, ml_model
from .preprocessing import SplitData

# Default tier thresholds on the ensemble probability of disease.
# 0.30 / 0.70 give a wide "moderate" middle band so borderline cases are
# routed to human review rather than auto-classified low or high.
DEFAULT_LOW_THRESHOLD = 0.30
DEFAULT_HIGH_THRESHOLD = 0.70
# |ml_prob - dl_prob| <= 0.20 = the two scorers agree within 20 percentage
# points; anything wider is flagged low-confidence to the clinician.
DEFAULT_AGREEMENT_TOLERANCE = 0.20


@dataclass
class PatientScore:
    ml_prob: float
    dl_prob: float
    ensemble_prob: float
    tier: str  # "low" | "moderate" | "high"
    confidence: str  # "high" | "low" — based on ml/dl agreement
    low_threshold: float
    high_threshold: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _tier(p: float, low: float, high: float) -> str:
    if p < low:
        return "low"
    if p >= high:
        return "high"
    return "moderate"


def score_patient(
    features: pd.DataFrame,
    ml_pipeline,
    dl_net,
    preprocessor,
    weights: tuple[float, float] = (0.5, 0.5),
    low_threshold: float = DEFAULT_LOW_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_THRESHOLD,
    agreement_tolerance: float = DEFAULT_AGREEMENT_TOLERANCE,
) -> PatientScore:
    """Score a single patient (one-row DataFrame) end-to-end."""
    if len(features) != 1:
        raise ValueError(f"score_patient expects a 1-row DataFrame, got {len(features)} rows")

    ml_prob = float(ml_model.predict_proba(ml_pipeline, features)[0])
    dl_prob = float(dl_model.predict_proba(dl_net, preprocessor, features)[0])

    w_ml, w_dl = weights
    ensemble = (w_ml * ml_prob + w_dl * dl_prob) / (w_ml + w_dl)
    confidence = "high" if abs(ml_prob - dl_prob) <= agreement_tolerance else "low"

    return PatientScore(
        ml_prob=ml_prob,
        dl_prob=dl_prob,
        ensemble_prob=ensemble,
        tier=_tier(ensemble, low_threshold, high_threshold),
        confidence=confidence,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )


def score_cohort(
    features: pd.DataFrame,
    ml_pipeline,
    dl_net,
    preprocessor,
    weights: tuple[float, float] = (0.5, 0.5),
    low_threshold: float = DEFAULT_LOW_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_THRESHOLD,
) -> pd.DataFrame:
    """Vectorised scoring for a cohort. Returns a DataFrame with the same index."""
    ml_probs = ml_model.predict_proba(ml_pipeline, features)
    dl_probs = dl_model.predict_proba(dl_net, preprocessor, features)
    w_ml, w_dl = weights
    ensemble = (w_ml * ml_probs + w_dl * dl_probs) / (w_ml + w_dl)
    tiers = [_tier(p, low_threshold, high_threshold) for p in ensemble]
    return pd.DataFrame(
        {
            "ml_prob": ml_probs,
            "dl_prob": dl_probs,
            "ensemble_prob": ensemble,
            "tier": tiers,
        },
        index=features.index,
    )


def load_default_scorers(split: SplitData) -> tuple[Any, Any, Any]:
    """Load persisted ML and DL artifacts, refit preprocessor on training split.

    The preprocessor is rebuilt from the SplitData rather than persisted so we
    avoid storing fitted scikit-learn objects that may drift across versions.
    """
    ml_pipeline = ml_model.load()
    dl_net = dl_model.load()
    return ml_pipeline, dl_net, split.preprocessor
