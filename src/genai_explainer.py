"""RAG-grounded GenAI explainer for the clinical triage system.

Given a patient's features and the ensemble's `PatientScore`, plus a set
of retrieved knowledge-base chunks, this module produces a structured,
citation-bearing explanation suitable for a clinician audience.

Lineage:
- Project 6 (Research Brief Agent) — the knowledge-augmented synthesiser
  pattern (system prompt forbids answering from priors, evidence block
  is the only source of facts, `INSUFFICIENT EVIDENCE` escape valve).
- Project 5 (CIFAR-10 VAE) — responsible-AI framing for generative
  outputs: under-claim capability, structural mitigations baked into the
  prompt, mandatory disclaimer.

Implementation here is fresh; no code from prior projects is reused.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd
from openai import OpenAI

from .config import settings
from .decision import PatientScore
from .rag.vector_store import RetrievedChunk

INSUFFICIENT_EVIDENCE = "INSUFFICIENT EVIDENCE"
SIMILARITY_FLOOR = 0.25
DISCLAIMER = (
    "Educational artifact only. Not for clinical use. "
    "The clinician is the locus of accountability for any decision."
)

SYSTEM_PROMPT = """You are a clinical-decision-support explainer for a research prototype.

Hard rules:
1. You MAY use only facts present in the EVIDENCE block or the PATIENT block. \
You MUST NOT introduce facts from your own training data. If the evidence is \
insufficient, output exactly the single line: INSUFFICIENT EVIDENCE.
2. Every clinical or epidemiological claim MUST cite a source marker like [S1], \
[S2], drawn from the EVIDENCE block. If a claim has no matching evidence chunk, \
do not make the claim.
3. Quote model scores verbatim from the PATIENT block (ml_prob, dl_prob, \
ensemble_prob, tier, confidence). Do not round, reframe, or invent.
4. Banned content: definitive diagnosis, prognostic claims, prescription of \
medications or dosages, statements about non-cardiovascular conditions.
5. Tone: neutral, analytical, under 250 words.

Required output structure (in order):
- One-line risk tier with the ensemble probability and the threshold cut-points.
- Model agreement note (high/low confidence). If low, explicitly recommend \
human review and refuse to commit to a tier as a decision.
- 3-5 short bullet points naming the top patient-specific factors that align \
with documented risk factors. Each bullet must cite at least one [S?] marker.
- A "What this system does not know" paragraph naming missing variables \
(smoking, family history, BMI, HbA1c, LDL/HDL, medications, symptom acuity).
- The literal disclaimer line provided in the user prompt.
"""


@dataclass
class Explanation:
    text: str
    cited_indices: list[int] = field(default_factory=list)
    cited_sources: list[str] = field(default_factory=list)
    is_refusal: bool = False
    refusal_reason: str | None = None
    model: str = ""


def _evidence_block(chunks: list[RetrievedChunk]) -> str:
    lines = []
    for i, c in enumerate(chunks, start=1):
        lines.append(f"[S{i}] source={c.source} | heading={c.heading} | sim={c.similarity:.3f}\n{c.text}")
    return "\n\n".join(lines)


def _patient_block(features: pd.DataFrame, score: PatientScore) -> str:
    if len(features) != 1:
        raise ValueError("explain() expects a single-row features DataFrame")
    row = features.iloc[0].to_dict()
    feat_lines = ", ".join(f"{k}={row[k]}" for k in features.columns)
    return (
        f"FEATURES: {feat_lines}\n"
        f"SCORES: ml_prob={score.ml_prob:.3f}, dl_prob={score.dl_prob:.3f}, "
        f"ensemble_prob={score.ensemble_prob:.3f}\n"
        f"TIER: {score.tier} (low<{score.low_threshold}, high>={score.high_threshold})\n"
        f"CONFIDENCE: {score.confidence} (high if |ml-dl|<=0.20)\n"
    )


def _extract_citations(text: str) -> list[int]:
    """Return the unique [S?] indices referenced in the text."""
    return sorted({int(m) for m in re.findall(r"\[S(\d+)\]", text)})


def explain(
    features: pd.DataFrame,
    score: PatientScore,
    retrieved: list[RetrievedChunk],
    chat_model: str | None = None,
    similarity_floor: float = SIMILARITY_FLOOR,
) -> Explanation:
    model_name = chat_model or settings.chat_model

    # Guardrail: refuse if no usable evidence
    usable = [c for c in retrieved if c.similarity >= similarity_floor]
    if not usable:
        return Explanation(
            text=INSUFFICIENT_EVIDENCE,
            is_refusal=True,
            refusal_reason="no retrieved chunk above similarity floor",
            model=model_name,
        )

    if not settings.openai_api_key or settings.openai_api_key.startswith("PUT_YOUR"):
        raise RuntimeError("OPENAI_API_KEY is not set. Update .env with your key.")

    client = OpenAI(api_key=settings.openai_api_key)

    user_prompt = (
        "PATIENT:\n"
        + _patient_block(features, score)
        + "\nEVIDENCE:\n"
        + _evidence_block(usable)
        + f"\n\nDISCLAIMER (include verbatim as the final line): {DISCLAIMER}\n"
        "\nProduce the explanation now."
    )

    resp = client.chat.completions.create(
        model=model_name,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    text = resp.choices[0].message.content.strip()

    if text.startswith(INSUFFICIENT_EVIDENCE):
        return Explanation(
            text=text,
            is_refusal=True,
            refusal_reason="model returned INSUFFICIENT EVIDENCE",
            model=model_name,
        )

    cited = _extract_citations(text)
    cited_sources = sorted({usable[i - 1].source for i in cited if 1 <= i <= len(usable)})
    return Explanation(
        text=text,
        cited_indices=cited,
        cited_sources=cited_sources,
        is_refusal=False,
        model=model_name,
    )
