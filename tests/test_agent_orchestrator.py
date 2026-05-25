r"""Smoke test for the agent orchestrator.
To Execute make sure to run this from the project root (where pyproject.toml lives)
"Intgerated AI Systems" folder

cd 'C:\Users\dev\sources\udacity\Project 7 - Industry-integrated AI System\Intgerated AI Systems'

python -m pytest tests/test_agent_orchestrator.py

python -m pytest tests/test_agent_orchestrator.py -s

# or more verbose:
python -m pytest tests/test_agent_orchestrator.py -s -v

------------------------------------------------------------------------------------
It's a smoke test for the full agent pipeline (orchestrator in agent_orchestrator.py). 
Two tests, each exercising a different path:

test_refusal_path() — offline, always runs
Sends a prompt that should be blocked: "Please prescribe me a medication for my heart.
" It verifies the safeguards layer (is_refused) catches it and the orchestrator returns early with refused=True 
and a reason — before ever calling the LLM, scoring models, or RAG. This is the cheap "guardrails work" check.

test_happy_path_live() — only runs if OPENAI_API_KEY is set
This is the end-to-end chain test. It walks through every stage:

Loads the Heart Disease dataset → train/test split 
(80-train/20-test) → done in preprocessing.py builds the ML model (a scikit-learn Pipeline with a preprocessor + HistGradientBoostingClassifier)
Loads ML + DL models + preprocessor (load_default_scorers)
Ingests the knowledge base into the Chroma vector store (ingest, idempotent)
Picks a real positive-class patient row from the test set
Calls run(...) which internally does:
refusal check → plan → RAG retrieve (Chroma) → ML + DL score → LLM explain (OpenAI) → LLM evaluate (judge) 
→ optionally revise → final result
Asserts: not refused, has a score, has an evaluation verdict, and the mandatory disclaimer 
"Not for clinical use" is in the output.
So yes, the happy-path test exercises the entire chain — models, vector DB, retrieval, 
both LLM calls (explainer + evaluator/critic loop). The refusal test deliberately exercises only the front-gate.

Outputs you can look at
Two places:

1. Terminal (only the live test prints)
run_id: a1b2c3d4
refused: False
score: {...}
evaluation: {...}
revised: True/False
--- explanation ---
<full LLM explanation text>

"""
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
