"""Smoke test for the agent orchestrator."""
from __future__ import annotations

from src.agent_orchestrator import run
from src.config import settings
from src.data_loader import load_heart_disease
from src.decision import load_default_scorers
from src.preprocessing import split_and_preprocess
from src.rag.retriever import ingest


def test_refusal_path():
    df = load_heart_disease()
    split = split_and_preprocess(df)
    ml, dl, pp = load_default_scorers(split)
    one = split.X_test.iloc[[0]]
    result = run("Please prescribe me a medication for my heart.", one, ml, dl, pp)
    assert result.refused is True
    assert result.refusal_reason is not None


def test_happy_path_live():
    if not settings.openai_api_key or settings.openai_api_key.startswith("PUT_YOUR"):
        print("skipping live test - OPENAI_API_KEY not set")
        return
    df = load_heart_disease()
    split = split_and_preprocess(df)
    ml, dl, pp = load_default_scorers(split)
    ingest()  # idempotent

    pos_idx = split.y_test[split.y_test == 1].index[0]
    one = split.X_test.loc[[pos_idx]]
    result = run("Summarise cardiovascular risk for this patient.", one, ml, dl, pp)
    print("run_id:", result.run_id)
    print("refused:", result.refused)
    print("score:", result.score)
    print("evaluation:", result.evaluation)
    print("revised:", result.revised)
    print("--- explanation ---")
    print(result.explanation["text"])
    assert not result.refused
    assert result.score is not None
    assert result.evaluation is not None
    assert "Not for clinical use" in result.explanation["text"]
