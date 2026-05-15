# Mentor Defense - Presentation Outline

**Integrative Industry Synthesis — Clinical Triage and Risk Decision Support**
**Format:** ~15 minutes talk + 10 minutes Q&A
**Audience:** Capstone mentor / employer-facing reviewer
**Companion artifact:** `docs/Reflective_Synthesis_Paper.pdf`

This outline is a roadmap for a live walkthrough; the verifiable evidence lives in the repo (notebooks, transcripts, run log, paper). Slides are optional - the live notebooks are the demo.

---

## Slide 1 - Title (30 s)
- Integrated AI System: Clinical-triage explainer for cardiovascular risk
- One-line framing: "Industry-grade AI inside a regulated workflow needs auditability, citations, refusal-before-LLM, and a logged audit trail - not a single brilliant model."
- Disclaimer: educational artifact, not for clinical use.

## Slide 2 - The problem (1 min)
- CVD = ~17.9 M deaths/year (WHO, 2021).
- Bottleneck at the front door is **clinician cognitive bandwidth**, not raw knowledge.
- Opportunity: a structured, evidence-grounded summary a clinician can accept/reject in seconds.
- Non-goal: replacing clinical judgement.

## Slide 3 - System architecture (2 min)
- Live: open `notebooks/05_integrated_pipeline.ipynb` and walk the mermaid diagram.
- Five blocks: preprocessing -> ML + DL -> ensemble + confidence -> agent (RAG + explainer + evaluator) -> persisted transcript.
- Emphasise: every block is small, individually testable, and produces a logged record.

## Slide 4 - Integration of prior projects (1.5 min)
- Show the lineage table from the synthesis paper.
- P2 -> IDA discipline; P3 -> sklearn pipeline + log1p; P4 -> dropout + disaggregated eval; P5 -> structurally-mitigated generation; P6 -> plan/retrieve/eval/revise loop.
- Key point: code was rebuilt from scratch; prior projects donated *patterns and constraints*, not source files.

## Slide 5 - Live demo: happy path (2 min)
- Re-run demo 1 from `notebooks/05_integrated_pipeline.ipynb` (or read transcript `docs/transcripts/demo1_happy_path_*.md`).
- Show: tier=high, confidence=high, citation-bearing explanation, mandatory disclaimer, evaluator passed 10/10.

## Slide 6 - Live demo: low confidence (2 min)
- Demo 2 transcript - ML and DL disagree (|0.97 - 0.62| > 0.20).
- Show: confidence=low surfaced, evaluator caught real issues in the first draft, one bounded revision passed.
- This is the **structural** mitigation - not prompt-only safety.

## Slide 7 - Live demo: refusal (1 min)
- Demo 3 transcript - banned request ("prescribe... dosage").
- Show: `refused=True`, `events=[request, refusal]`, **no LLM call was made**.
- This is what makes the safety story auditable.

## Slide 8 - Quantitative evaluation (2 min)
- Open `notebooks/04_evaluation.ipynb`.
- Headline: ML and DL ROC-AUC 0.96, Brier ~0.087 on n=61.
- **Per-sex gap** in *both* models -> data-driven, not model-driven; surfaced in retrieved model card.
- **Failure cases** - top-5 highest-confidence wrongs are largely shared between ML and DL.
- **RAG faithfulness** - across 3 live runs: zero invalid citations, 36-44% explanation/evidence token overlap.

## Slide 9 - Ethics, governance, responsible AI (1.5 min)
- Five structural mitigations: refusal-before-LLM, citation discipline, mandatory disclaimer, confidence surfacing, full audit trail.
- Map onto NIST AI RMF (govern/map/measure/manage) and EU AI Act high-risk requirements (transparency, accountability, human oversight).
- Honest limitations: tiny dataset, calibration smell on confident wrongs, substring refusal can be paraphrased past, KB is synthetic.

## Slide 10 - Industry relevance and what I would build next (1 min)
- Pattern (small classical model + RAG + structurally-guarded LLM + evaluator-critic) is the same one being adopted in legal, financial, insurance for the same regulatory reasons.
- Future work: calibration layer, bootstrap CIs, real KB, classifier-based input filter, counterfactual explanations, human-in-the-loop feedback capture.

## Slide 11 - Q&A (10 min)

### Anticipated questions and answers

**Q: Why two models if they tie on ROC-AUC?**
A: The headline tie hides per-row disagreement. The disagreement signal is what powers the low-confidence flag; without two architecturally different learners we would have no structural way to detect borderline cases.

**Q: Why RAG instead of fine-tuning?**
A: Auditability and revisability. Clinicians can edit a markdown file and the change takes effect on the next call. Fine-tuned weights cannot be edited, cannot cite their sources, and cannot be revised without retraining.

**Q: How do you know the LLM is not hallucinating citations?**
A: I check it. `src/evaluation.py:rag_faithfulness` parses every `[S?]` index and verifies it is within range of the retrieved chunks. Across 3 live runs in `notebooks/04_evaluation.ipynb`, zero invalid citations.

**Q: What stops a user from prompt-injecting past the refusal list?**
A: Nothing perfect. The substring check happens **before** the LLM, so it cannot be talked out of. A determined adversary can paraphrase past it; the mitigation is that the system is gated behind a clinician, and a real deployment would replace the substring check with a classifier-based filter.

**Q: Is this clinically valid?**
A: No. It is an educational artifact on a 30-year-old benchmark with n=303. No clinical claim is made anywhere in the system, the disclaimer is mandatory, and the limitations are documented in the paper.

**Q: What was the hardest design decision?**
A: Choosing structural mitigations over prompt-only ones. Adding "please cite sources" to a prompt is a few lines; building an evaluator-critic loop with a logged JSON verdict and a bounded revision step is significantly more code, but it is the only one a regulator can audit.
