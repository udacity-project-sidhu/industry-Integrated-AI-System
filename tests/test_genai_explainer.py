"""Smoke test for the RAG-grounded GenAI explainer.

cd 'C:\Users\dev\sources\udacity\Project 7 - Industry-integrated AI System\Intgerated AI Systems'

python -m pytest tests/test_genai_explainer.py

python -m pytest tests/test_genai_explainer.py -s

# or more verbose:
python -m pytest tests/test_genai_explainer.py -s -v

Hits the live OpenAI chat + embeddings API once.
Skipped automatically if OPENAI_API_KEY is not set.

--------------------------------------------------------------------------------

See notes at the bottom of this file about what this function does.
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


"""
Smoke tests for genai_explainer.py — the RAG-grounded LLM explainer that turns a PatientScore plus retrieved knowledge-base chunks into a clinician-facing natural-language explanation. Two tests, one offline and one live.

1. test_refuses_on_empty_evidence() — offline, always runs
Hands the explainer a synthetic patient + score but zero retrieved chunks (retrieved=[]). Asserts:

result.is_refusal is True,
The text is exactly the canonical INSUFFICIENT_EVIDENCE string.
This validates the fail-closed guardrail: if the RAG step returns nothing relevant, the explainer must refuse rather than invent content. This is the anti-hallucination front line — it never reaches the LLM at all in this path.

2. test_live_explanation() — only runs if OPENAI_API_KEY is set
End-to-end check of the real explanation pipeline (this is the test that costs money):

Load + split the dataset, load the default ML/DL/preprocessor bundle.
Pick a positive-class patient from the test set (so the explanation has substance to discuss).
Compute the ensemble PatientScore for that patient.
ingest() the knowledge base into Chroma (idempotent — no-op if already indexed).
Build a query string from the patient's cardiac-relevant features (cp, thal, exang, oldpeak) and search() the vector store for top-4 chunks.
Call explain(features, score, chunks) — this is the real OpenAI chat + embeddings round-trip.
Print the explanation and citation metadata, then assert:
Not a refusal,
At least one citation was made (cited_indices non-empty → grounded in retrieved evidence),
Mandatory "Not for clinical use" disclaimer is present.
What it does NOT test
Exact wording / quality of the explanation (LLMs are stochastic).
The evaluator/critic loop or revision (that's test_agent_orchestrator.py).
Numeric scoring (that's test_decision.py).
Refusal prompts (banned-topic detection in safeguards.py — that's test_safeguards.py and the orchestrator test).
Outputs
Refusal test: pure pass/fail.
Live test: prints the patient score, the full explanation text, cited chunk indices, and cited sources to the terminal (only visible with -s).
No JSONL log here — that's the orchestrator's job. This isolates the explainer alone.
Cost / time
Refusal test: milliseconds, no network.
Live test: one chat completion + a small embeddings call against OpenAI. Skipped cleanly when no key is configured, so it's safe to leave in the default test run.
What this isolates
This file pins down the explainer's two most important contracts:

No evidence → refusal (it never tries to fabricate).
Real evidence → grounded, cited, disclaimed output.
Anything related to scoring, safeguards, or the critic loop is intentionally out of scope and tested elsewhere.

"""