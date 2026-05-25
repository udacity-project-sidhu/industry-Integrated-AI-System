"""UCI Heart Disease data loader.

Fetches the UCI Heart Disease dataset via `ucimlrepo` and caches it to
`data/raw/heart_disease.csv` so subsequent runs are offline.

Lineage: the structured "load → inspect → cache" discipline follows the
Initial Data Analysis pattern adopted in Project 2 (Data & Statistical
Reasoning, UCI Bank Marketing).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import settings # dot is used for relative path pointing to current direct

RAW_CSV = settings.data_raw / "heart_disease.csv"
UCI_HEART_DISEASE_ID = 45


def load_heart_disease(force_refresh: bool = False) -> pd.DataFrame:
    """Load the UCI Heart Disease dataset as a single DataFrame.

    The original `num` target (0..4 severity) is preserved as `num` and a
    binary `target` column is added (0 = no disease, 1 = disease present).
    """
    settings.data_raw.mkdir(parents=True, exist_ok=True)

    if RAW_CSV.exists() and not force_refresh:
        return pd.read_csv(RAW_CSV)

    # Local file not found, fetch from UCI ML Repo and cache to disk for next time.
    from ucimlrepo import fetch_ucirepo

    repo = fetch_ucirepo(id=UCI_HEART_DISEASE_ID)
    features = repo.data.features    # pandas DataFrame: the X columns
    targets = repo.data.targets      # pandas Series: the y column (0..4 original severity labels)

    # Two steps: rejoin the X and y the loader handed back separately, then derive a clean binary label from the original multi-class severity score.
    df = pd.concat([features, targets], axis=1)
    if "num" in df.columns:
        df["target"] = (df["num"] > 0).astype(int)

    df.to_csv(RAW_CSV, index=False)
    return df


FEATURE_DICTIONARY: dict[str, str] = {
    "age": "Age in years.",
    "sex": "Sex (1 = male, 0 = female).",
    "cp": "Chest pain type (1 typical angina, 2 atypical, 3 non-anginal, 4 asymptomatic).",
    "trestbps": "Resting blood pressure on admission (mm Hg).",
    "chol": "Serum cholesterol (mg/dl).",
    "fbs": "Fasting blood sugar > 120 mg/dl (1 = true, 0 = false).",
    "restecg": "Resting electrocardiographic results (0 normal, 1 ST-T abnormality, 2 LV hypertrophy).",
    "thalach": "Maximum heart rate achieved during exercise.",
    "exang": "Exercise-induced angina (1 = yes, 0 = no).",
    "oldpeak": "ST depression induced by exercise relative to rest.",
    "slope": "Slope of the peak exercise ST segment (1 up, 2 flat, 3 down).",
    "ca": "Number of major vessels (0-3) colored by fluoroscopy.",
    "thal": "Thalassemia (3 normal, 6 fixed defect, 7 reversible defect).",
    "num": "Original severity target (0-4); 0 = no disease, >0 = disease present.",
    "target": "Binary outcome derived from `num` (1 = disease present).",
}

NUMERIC_FEATURES: list[str] = ["age", "trestbps", "chol", "thalach", "oldpeak"]
CATEGORICAL_FEATURES: list[str] = [
    "sex",
    "cp",
    "fbs",
    "restecg",
    "exang",
    "slope",
    "ca",
    "thal",
]
TARGET_COL: str = "target"


def feature_columns() -> list[str]:
    return NUMERIC_FEATURES + CATEGORICAL_FEATURES
