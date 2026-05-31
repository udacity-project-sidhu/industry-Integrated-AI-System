# Rehearsal Script — Project 8 Defense

**This is the single canonical script to rehearse from.** All earlier outline variants in `docs/` are kept for reference; this file supersedes them for the live defense.

- **Time budget:** 14 min talk + 1 min buffer + 15 min Q&A.
- **Companion deck:** `Defense_Deck.pptx` (same folder).
- **Demo fallback (if live notebook fails):** read transcripts in `transcripts/`.
- **Paper:** `Reflective_Synthesis_Paper.pdf` (same folder).

---

## Slide 1 — Title (0:00, 30 s)
> "I'll walk through a clinical-triage explainer for cardiovascular risk. It's an integrated AI system, not a single model. The headline I want to defend is that industry-pattern AI inside a regulated workflow needs *structural* properties — auditability, citations, refusal before the LLM, a logged trail — and those properties are what the architecture provides, not what the prompt provides. Educational artifact only; not for clinical use."

## Slide 2 — Industry context & problem (0:30, 1:00)
- CVD: ~17.9 M deaths/year (WHO 2021).
- Bottleneck = clinician cognitive bandwidth, not raw knowledge.
- Goal: structured, evidence-grounded summary a clinician accepts or rejects in seconds.
- Non-goal: replacing clinical judgment.
- Why AI: structured tabular signal + retrievable knowledge + natural-language summarisation.

## Slide 3 — System overview (1:30, 2:00)
- Show `architecture.png`.
- Five blocks: **Preprocessing → ML + DL → Ensemble + Confidence → Agent (RAG + Explainer + Evaluator) → Persisted Transcript**.
- Every block is small, individually testable, emits a logged event.
- No monolithic step → regulators can audit each stage.

## Slide 4 — Integration of prior capstones (3:30, 1:30)
| Prior project | Contribution | Where used |
|---|---|---|
| **P2** Statistical reasoning | IDA discipline, chi-square + Cramer's V | `notebooks/01_data_exploration.ipynb` |
| **P3** ML / RFM | sklearn `Pipeline`, `log1p` skew handling | `src/preprocessing.py`, `src/ml_model.py` |
| **P4** Deep Learning | Dropout, disaggregated per-slice eval | `src/dl_model.py`, `src/evaluation.py` |
| **P5** Generative AI | Structural mitigations for generative output | `src/genai_explainer.py` guardrails |
| **P6** Agentic AI | Plan → Retrieve → Evaluate → Revise loop, RAG, refusal list | `src/rag/`, `src/agent_orchestrator.py` |

- Five projects integrated (≥3 required).
- Code rebuilt from scratch; what is reused is *patterns and design discipline*, not source files.

## Slide 5 — Demo 1: high risk, self-corrected (5:00, 2:00)
- Open `notebooks/05_integrated_pipeline.ipynb` *or* read `transcripts/demo1_happy_path.md`.
- High-risk patient: `ml_prob 0.990` vs `dl_prob 0.610` → |Δ| = 0.38 → ensemble 0.800, tier = **high**, confidence = **low**.
- First draft made an ungrounded clinical claim (`thalach` 156 "above age-predicted maximum") — no retrieved chunk supports it.
- Evaluator (`gpt-4o`) caught it, scored 7/10, listed 3 issues, issued revision instructions; explainer (`gpt-4o-mini`) produced a hedged, grounded rewrite in one bounded revision.
- Defense point: evaluator is a *different* LLM than the explainer — not rubber-stamping itself — and the revision cap prevents loops.

## Slide 6 — Demo 2: borderline tier, format discipline (7:00, 2:00)
- Borderline patient: `ml_prob 0.825` vs `dl_prob 0.336` → |Δ| = 0.49 → ensemble 0.581, tier = **moderate**, confidence = **low**.
- System refuses to commit to a tier-as-decision: final text says *"unable to commit to a tier as a decision; human review recommended"*.
- First draft failed evaluator on **format discipline** (missing inline citations; model scores not quoted verbatim) — not on clinical content.
- One bounded revision (cap = 1) fixes it; the system does not loop indefinitely.
- Key point: every safety check — disagreement gate, citation check, verbatim-score rule, revision cap — lives in code, not in the prompt.

## Slide 7 — Demo 3: refusal (9:00, 1:00)
- Request: "prescribe… dosage".
- Transcript shows `refused = True`, exactly two events: `request`, `refusal`. **No LLM call.**
- Substring check in `src/safeguards.py` runs *before* any model code → cannot be talked out of refusing.

## Slide 8 — Quantitative evaluation (10:00, 1:30)
- ROC-AUC ≈ 0.96 (ML and DL), Brier ≈ 0.087, n = 61 test rows.
- 95% bootstrap CIs alongside a LogisticRegression baseline → bands overlap, so I am **not** overselling gradient boosting.
- Per-sex slice gap appears in **both** models → data-driven, not model-driven; disclosed in the retrieved model card.
- Top failure cases largely shared between ML and DL — also a data signal.
- RAG faithfulness across 3 live runs: **zero** invalid citations, 37–45 % explanation/evidence token overlap.

## Slide 9 — Ethics & responsible AI (11:30, 1:30)
Five structural mitigations:
1. Refusal before LLM.
2. Citation discipline (`[S?]` indices verified).
3. Mandatory disclaimer.
4. Confidence flag surfaced to clinician.
5. Full JSONL audit trail (`outputs/run_log.jsonl`).

Mapped to: **NIST AI RMF** (govern, map, measure, manage) and **EU AI Act** high-risk requirements (transparency, human oversight, accountability).

Honest limitations: tiny benchmark (n=303), calibration smell on confident-wrong cases, substring refusal can be paraphrased past, KB is synthetic.

## Slide 10 — Industry relevance & next steps (13:00, 1:00)
- Pattern (small classical model + RAG + structurally-guarded LLM + evaluator-critic) is the same one being adopted in legal, financial advisory, insurance — same regulatory drivers.
- Transferable lesson: **the architecture is the safety story**.
- Future work, prioritised:
  1. Calibration layer.
  2. Real curated KB.
  3. Classifier-based input filter (replace substring list).
  4. Counterfactual explanations.
  5. Human-in-the-loop feedback channel.

## Slide 11 — Thank you / Q&A (14:00, 15 min)

---

## Anticipated Q&A (rehearse these answers verbatim)

**Q1. Why two models if they tie on ROC-AUC?**
A. Headline tie hides per-row disagreement. That disagreement powers the low-confidence flag; without two architecturally different learners we have no structural way to detect borderline cases.

**Q2. Why RAG instead of fine-tuning?**
A. Auditability and revisability. Clinicians edit a markdown file and the change takes effect on the next call. Fine-tuned weights can't be edited, cited, or revised without retraining.

**Q3. How do you know the LLM is not hallucinating citations?**
A. I check it. `src/evaluation.py:rag_faithfulness` parses every `[S?]` index and verifies it is within range of the retrieved chunks. Across 3 live runs: zero invalid citations.

**Q4. What stops a user prompt-injecting past the refusal list?**
A. Nothing perfect. Substring check happens *before* the LLM, so it can't be talked out of. A determined adversary can paraphrase past it — mitigation is that the system is gated behind a clinician, and production would replace the substring check with a classifier-based filter.

**Q5. Is this clinically valid?**
A. No. Educational artifact on a 30-year-old benchmark with n=303. No clinical claim is made; the disclaimer is mandatory; limitations are documented in the paper.

**Q6. Hardest design decision?**
A. Choosing structural mitigations over prompt-only ones. Adding "please cite sources" to a prompt is a few lines; building an evaluator-critic loop with a logged JSON verdict and a bounded revision step is significantly more code — but it is the only one a regulator can audit.

**Q7. What would you do differently next time?**
A. Add a calibration layer before reporting probabilities, and replace the synthetic KB with a curated one before any quantitative claim about RAG faithfulness leaves the educational context.

---

## Delivery checklist (run morning of the defense)

- [ ] Notebook 05 runs end-to-end with current API keys.
- [ ] `outputs/run_log.jsonl` has at least 3 recent rows.
- [ ] `Defense_Deck.pptx` opens cleanly.
- [ ] Transcripts in `transcripts/` open in editor as fallback.
- [ ] Microphone test in defense language (English).
- [ ] Timer visible during talk.
