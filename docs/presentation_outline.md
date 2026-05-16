# Mentor Defense - Presentation Outline

**Integrative Industry Synthesis — Clinical Triage and Risk Decision Support**
**Format:** ~15 minutes talk + 10 minutes Q&A
**Audience:** Capstone mentor / employer-facing reviewer
**Companion artifact:** `docs/Reflective_Synthesis_Paper.pdf`

This outline is a roadmap for a live walkthrough; the verifiable evidence lives in the repo (notebooks, transcripts, run log, paper). Slides are optional - the live notebooks are the demo.

---

## Slide 1 - Title (30 s)
- Integrated AI System: Clinical-triage explainer for cardiovascular risk
- One-line framing: "Industry-pattern AI inside a regulated workflow needs auditability, citations, refusal-before-LLM, and a logged audit trail - not a single brilliant model."
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

---

## Appendix — Speaker notes (one paragraph per slide)

These are the lines I actually intend to say on the day. Each note tracks roughly to the slide's timing budget above.

**Slide 1 (Title, 30 s).** "I'll walk you through a clinical-triage explainer for cardiovascular risk. It is an integrated AI system, not a single model. The headline I want to defend today is that industry-pattern AI inside a regulated workflow needs *structural* properties — auditability, citations, refusal before the LLM, a logged trail — and that those properties are what the architecture provides, not what the prompt provides. Educational artifact only; not for clinical use."

**Slide 2 (Problem, 1 min).** "Cardiovascular disease is the leading cause of death globally — roughly 17.9 million deaths a year per WHO 2021. The bottleneck at the front door of a hospital is not raw clinical knowledge; it is cognitive bandwidth. A triage clinician sees hundreds of patients a shift. The opportunity here is a structured, evidence-grounded summary a clinician can accept or reject in seconds. The non-goal — which I'll be explicit about — is replacing clinical judgement. That would be neither legal nor ethical."

**Slide 3 (Architecture, 2 min).** "Open `notebooks/05_integrated_pipeline.ipynb` and walk the diagram. Five blocks: preprocessing → ML + DL → ensemble with confidence flag → agent loop with RAG, explainer, evaluator → persisted transcript. The point I want to land is that every block is small, individually testable, and emits a logged event. There is no single monolithic step. That is the part regulators care about."

**Slide 4 (Integration, 1.5 min).** "Show the lineage table. P2 contributed initial-data-analysis discipline and the chi-square + Cramer's V framing in nb01. P3 contributed the sklearn `Pipeline` + `ColumnTransformer` and the `log1p` skew handling in `src/preprocessing.py`. P4 contributed dropout regularisation and the disaggregated per-slice evaluation pattern. P5 contributed the structural-mitigation mindset for generative output. P6 contributed the plan-retrieve-evaluate-revise loop now in `src/agent_orchestrator.py`. The code is rebuilt — what was reused is patterns and design discipline, not source files."

**Slide 5 (Happy path, 2 min).** "Re-run demo 1 from `notebooks/05_integrated_pipeline.ipynb` or open the transcript in `docs/transcripts/demo1_happy_path_*.md`. Tier is high, ensemble confidence is high, models agree. Explanation is grounded in retrieved evidence chunks with `[S?]` citations, ends with the mandatory disclaimer, evaluator passed at 10/10. Importantly, the evaluator runs on a *different* LLM snapshot (`gpt-4o`) than the explainer (`gpt-4o-mini`) — it is not rubber-stamping its own output."

**Slide 6 (Low confidence, 2 min).** "Demo 2 — ML says 0.97, DL says 0.62, the ensemble agreement gate flips to low. The first draft fails the evaluator on a real issue. One bounded revision (cap = 1) fixes it. The point I want to defend here is that this is *structural*: the disagreement check is in the decision layer, the evaluator is in the orchestrator, the revision limit is a runtime cap — none of this lives in the prompt. Prompt-only safety wouldn't survive contact with an adversarial user; this design does."

**Slide 7 (Refusal, 1 min).** "Demo 3 — request asks for prescription dosage. The transcript shows `refused = True` and exactly two events: `request` and `refusal`. There is **no LLM call**. The check is a substring match in `src/safeguards.py` that runs before any model code. That is the property that makes this auditable — you cannot talk the system out of refusing because the LLM never gets a chance to decide."

**Slide 8 (Evaluation, 2 min).** "Open `notebooks/04_evaluation.ipynb`. Headline ROC-AUC sits around 0.96 for ML and DL, Brier ~0.087 on a 61-row test set. Importantly I now report 95% bootstrap CIs alongside a LogisticRegression baseline — and the bands overlap, so I'm not overselling the gradient-boosting model. The per-sex slice gap appears in *both* models, which tells me it's data-driven, not model-driven; the retrieved model card discloses it. Top failure cases are mostly shared between ML and DL — also a data signal. RAG faithfulness across three live runs: zero invalid citations, 36–44% explanation/evidence token overlap."

**Slide 9 (Ethics, 1.5 min).** "Five structural mitigations: refusal before LLM, citation discipline (`[S?]` indices verified), mandatory disclaimer, confidence flag surfaced to the clinician, full JSONL audit trail. These map onto NIST AI RMF (govern, map, measure, manage) and onto the EU AI Act's high-risk requirements (transparency, human oversight, accountability). I deliberately list limitations: tiny benchmark dataset, calibration smell on confident-wrong cases, substring refusal can be paraphrased past by an adversary, knowledge base is synthetic. The mitigations are honest about what they don't fix."

**Slide 10 (Industry relevance, 1 min).** "This pattern — small classical model plus RAG plus structurally-guarded LLM plus evaluator-critic — is the same pattern being adopted in legal, financial advisory, and insurance for exactly the same regulatory reasons. The transferable lesson for an entry-level data scientist is that *the architecture is the safety story*. Future extensions, in priority order: calibration layer, a real curated KB, classifier-based input filter to replace the substring list, counterfactual explanations, and a human-in-the-loop feedback channel."

**Slide 11 (Q&A, 10 min).** Use the anticipated-question answers above as the seed; for anything off-script, anchor the answer back to a file path in the repo (e.g. "that's enforced in `src/safeguards.py` line ..." or "you can see it in `outputs/run_log.jsonl`"). The defense story is: every claim points to a runnable artifact.
