"""Agent orchestrator for the clinical-triage explainer.

Workflow (P6 plan-and-execute with evaluator/critic loop, rebuilt fresh):

    refusal check
       v
    plan (fixed mini-plan for this domain)
       v
    rag_search   --+
    score_patient  +-> evidence + scores
       v          --+
    explain (LLM, grounded in evidence)
       v
    evaluate (LLM-as-judge against safeguards.RUBRIC)
       v             pass
       +-------------------> final explanation
       |
       fail (within revision cap)
       v
    revise (one-shot)
       v
    final explanation (+ evaluator verdict attached)

Every step writes a JSONL record to `outputs/run_log.jsonl`.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from openai import OpenAI

from .config import settings
from .decision import PatientScore, score_patient
from .genai_explainer import (
    DISCLAIMER,
    INSUFFICIENT_EVIDENCE,
    SYSTEM_PROMPT,
    Explanation,
    _evidence_block,
    _patient_block,
    explain,
)
from .rag.retriever import search
from .rag.vector_store import RetrievedChunk
from .safeguards import CAPS, RUBRIC, is_refused

RUN_LOG = settings.project_root / "outputs" / "run_log.jsonl"
EVALUATOR_SYSTEM_PROMPT = """You evaluate a clinical-triage explanation against a rubric.

Return a single JSON object with keys:
  pass: boolean
  score: integer 0-10
  issues: list of short strings naming problems (empty if pass=true)
  instructions: string with concrete revision instructions (empty if pass=true)

Pass condition: score >= 8 AND no critical issues. Critical issues include
missing citations, unsupported claims, banned content, fabricated scores,
or low-confidence cases that fail to surface uncertainty.

Output ONLY the JSON object, no surrounding prose.
"""


@dataclass
class RunResult:
    run_id: str
    refused: bool
    refusal_reason: str | None
    score: dict | None
    explanation: dict | None
    evaluation: dict | None
    revised: bool
    events: list[dict] = field(default_factory=list)


def _log(events: list[dict], run_id: str, event: str, payload: dict) -> None:
    record = {"ts": time.time(), "run_id": run_id, "event": event, **payload}
    events.append(record)
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _evaluator_call(
    client: OpenAI, model_name: str, explanation_text: str, evidence_block: str, patient_block: str
) -> dict:
    user_prompt = (
        f"RUBRIC:\n{RUBRIC}\n\n"
        f"PATIENT:\n{patient_block}\n\n"
        f"EVIDENCE:\n{evidence_block}\n\n"
        f"EXPLANATION:\n{explanation_text}\n\n"
        "Return the JSON verdict now."
    )
    resp = client.chat.completions.create(
        model=model_name,
        temperature=0.0,
        messages=[
            {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return {"pass": False, "score": 0, "issues": ["evaluator JSON parse failed"], "instructions": "Reformat output."}


def _revise(
    client: OpenAI,
    model_name: str,
    original: str,
    instructions: str,
    patient_block: str,
    evidence_block: str,
) -> str:
    user_prompt = (
        f"PATIENT:\n{patient_block}\n\nEVIDENCE:\n{evidence_block}\n\n"
        f"ORIGINAL EXPLANATION:\n{original}\n\n"
        f"REVISION INSTRUCTIONS:\n{instructions}\n\n"
        f"DISCLAIMER (include verbatim as the final line): {DISCLAIMER}\n\n"
        "Produce a corrected explanation that satisfies every rubric item. "
        "Hard rules in the system prompt still apply."
    )
    resp = client.chat.completions.create(
        model=model_name,
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content.strip()


def _build_query(features: pd.DataFrame) -> str:
    row = features.iloc[0]
    parts = []
    for col in ("cp", "thal", "exang", "oldpeak", "slope", "ca"):
        if col in features.columns:
            parts.append(f"{col}={row[col]}")
    return "Cardiovascular risk explanation for " + ", ".join(parts)


def run(
    user_request: str,
    features: pd.DataFrame,
    ml_pipeline,
    dl_net,
    preprocessor,
    chat_model: str | None = None,
) -> RunResult:
    """End-to-end run: refusal check -> retrieve -> score -> explain -> evaluate -> (revise)."""
    run_id = uuid.uuid4().hex[:8]
    events: list[dict] = []
    model_name = chat_model or settings.chat_model

    _log(events, run_id, "request", {"user_request": user_request, "n_features_rows": len(features)})

    refused, reason = is_refused(user_request)
    if refused:
        _log(events, run_id, "refusal", {"reason": reason})
        return RunResult(
            run_id=run_id,
            refused=True,
            refusal_reason=f"matched refusal substring: {reason}",
            score=None,
            explanation=None,
            evaluation=None,
            revised=False,
            events=events,
        )

    if len(features) != 1:
        _log(events, run_id, "validation_error", {"n_rows": len(features)})
        return RunResult(
            run_id=run_id,
            refused=True,
            refusal_reason="expected a single-row patient feature frame",
            score=None,
            explanation=None,
            evaluation=None,
            revised=False,
            events=events,
        )

    # Score
    patient_score: PatientScore = score_patient(features, ml_pipeline, dl_net, preprocessor)
    _log(events, run_id, "score", patient_score.to_dict())

    # Retrieve
    query_text = _build_query(features)
    chunks: list[RetrievedChunk] = search(query_text, k=CAPS.retrieval_k)
    _log(
        events,
        run_id,
        "rag_search",
        {"query": query_text, "n_results": len(chunks), "sources": [c.source for c in chunks]},
    )

    # Explain
    expl: Explanation = explain(features, patient_score, chunks, chat_model=model_name)
    _log(events, run_id, "draft", {"is_refusal": expl.is_refusal, "text": expl.text, "cited_sources": expl.cited_sources})

    if expl.is_refusal:
        return RunResult(
            run_id=run_id,
            refused=False,
            refusal_reason=None,
            score=patient_score.to_dict(),
            explanation=asdict(expl),
            evaluation=None,
            revised=False,
            events=events,
        )

    # Evaluate
    if not settings.openai_api_key or settings.openai_api_key.startswith("PUT_YOUR"):
        raise RuntimeError("OPENAI_API_KEY is not set.")
    client = OpenAI(api_key=settings.openai_api_key)

    # Drop low-similarity chunks before citing: <0.25 cosine is usually off-topic
    # noise that would tempt the LLM into ungrounded claims.
    usable = [c for c in chunks if c.similarity >= 0.25]
    evidence_block = _evidence_block(usable)
    patient_block = _patient_block(features, patient_score)

    verdict = _evaluator_call(client, model_name, expl.text, evidence_block, patient_block)
    _log(events, run_id, "evaluation", verdict)

    revised = False
    if not verdict.get("pass", False) and CAPS.max_revisions > 0:
        revised_text = _revise(
            client,
            model_name,
            original=expl.text,
            instructions=verdict.get("instructions", "Address the listed issues."),
            patient_block=patient_block,
            evidence_block=evidence_block,
        )
        revised = True
        expl = Explanation(
            text=revised_text,
            cited_indices=sorted({int(m) for m in re.findall(r"\[S(\d+)\]", revised_text)}),
            cited_sources=sorted({usable[i - 1].source for i in sorted({int(m) for m in re.findall(r"\[S(\d+)\]", revised_text)}) if 1 <= i <= len(usable)}),
            is_refusal=revised_text.startswith(INSUFFICIENT_EVIDENCE),
            model=model_name,
        )
        _log(events, run_id, "revision", {"text": expl.text, "cited_sources": expl.cited_sources})

    return RunResult(
        run_id=run_id,
        refused=False,
        refusal_reason=None,
        score=patient_score.to_dict(),
        explanation=asdict(expl),
        evaluation=verdict,
        revised=revised,
        events=events,
    )
