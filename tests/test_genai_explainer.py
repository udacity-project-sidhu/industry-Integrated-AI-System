"""Smoke test for the RAG-grounded GenAI explainer.

Hits the live OpenAI chat + embeddings API once.
Skipped automatically if OPENAI_API_KEY is not set.
"""
from __future__ import annotations

from src.config import settings
from src.data_loader import load_heart_disease
from src.decision import load_default_scorers, score_patient
from src.genai_explainer import INSUFFICIENT_EVIDENCE, Explanation, explain
from src.preprocessing import split_and_preprocess
from src.rag.retriever import ingest, search
from src.rag.vector_store import RetrievedChunk


def test_refuses_on_empty_evidence():
    # Build a minimal score with synthetic features
    import pandas as pd
    from src.decision import PatientScore

    features = pd.DataFrame([{"age": 55, "sex": 1, "cp": 4, "trestbps": 140, "chol": 240, "fbs": 0, "restecg": 0, "thalach": 150, "exang": 1, "oldpeak": 1.5, "slope": 2, "ca": 1, "thal": 7}])
    score = PatientScore(0.6, 0.55, 0.575, "moderate", "high", 0.3, 0.7)
    result = explain(features, score, retrieved=[])
    assert result.is_refusal
    assert result.text == INSUFFICIENT_EVIDENCE


def test_live_explanation():
    if not settings.openai_api_key or settings.openai_api_key.startswith("PUT_YOUR"):
        print("skipping live test - OPENAI_API_KEY not set")
        return

    df = load_heart_disease()
    split = split_and_preprocess(df)
    ml, dl, pp = load_default_scorers(split)

    # Pick a positive test-set example for a richer explanation
    pos_idx = split.y_test[split.y_test == 1].index[0]
    features = split.X_test.loc[[pos_idx]]
    score = score_patient(features, ml, dl, pp)
    print("score:", score)

    ingest()  # idempotent
    query_text = (
        f"Cardiovascular risk explanation: chest pain cp={features.iloc[0]['cp']}, "
        f"thal={features.iloc[0]['thal']}, exang={features.iloc[0]['exang']}, "
        f"oldpeak={features.iloc[0]['oldpeak']}"
    )
    chunks = search(query_text, k=4)
    result: Explanation = explain(features, score, chunks)
    print("--- explanation ---")
    print(result.text)
    print("--- meta ---")
    print("cited indices:", result.cited_indices)
    print("cited sources:", result.cited_sources)
    print("is_refusal:", result.is_refusal)
    assert not result.is_refusal
    assert len(result.cited_indices) > 0
    assert "Not for clinical use" in result.text
