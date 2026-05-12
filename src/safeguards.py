"""Safeguards for the agent orchestrator.

Refusal substrings, runtime caps, and the evaluator rubric for the
clinical-triage explainer.

Lineage: P6 (Research Brief Agent) — substring refusal list + runtime
caps + verbatim rubric in source. Implementation here is a fresh,
domain-specific (healthcare) version.
"""
from __future__ import annotations

from dataclasses import dataclass

# Substring match (case-insensitive) — if any appears in the user request,
# the orchestrator refuses before any LLM call.
REFUSAL_SUBSTRINGS: tuple[str, ...] = (
    "diagnose me",
    "diagnose this patient",
    "give me a diagnosis",
    "what medication",
    "prescribe",
    "dosage",
    "should i take",
    "legal advice",
    "investment advice",
    "self-harm",
    "kill myself",
    "weapon",
    "bioweapon",
)


@dataclass(frozen=True)
class RuntimeCaps:
    max_retrieval_calls: int = 4
    max_revisions: int = 1
    retrieval_k: int = 4


CAPS = RuntimeCaps()


# Verbatim rubric passed to the evaluator. Edit here to change pass criteria.
RUBRIC: str = """\
1. The explanation directly addresses the patient's risk based on the supplied features and ensemble score.
2. Every clinical claim has an inline [S?] citation that maps to the EVIDENCE block.
3. The model scores (ml_prob, dl_prob, ensemble_prob) are quoted verbatim — not rounded, reframed, or invented.
4. Required structure is present and in order: one-line tier, model-agreement note, 3-5 cited risk-factor bullets, "what this system does not know" paragraph, disclaimer line.
5. No banned content: no definitive diagnosis, no prognostic claim, no medication/dose, no non-cardiovascular statements.
6. Low-confidence cases (|ml-dl|>0.20) explicitly surface uncertainty and recommend human review.
7. Tone is neutral and analytical; explanation is under 250 words.
"""


def is_refused(text: str) -> tuple[bool, str | None]:
    lower = text.lower()
    for needle in REFUSAL_SUBSTRINGS:
        if needle in lower:
            return True, needle
    return False, None
