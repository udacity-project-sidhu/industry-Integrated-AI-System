# Defense FAQ — Project 8 Mentor Defense

Every answer ends with **[Show]** = file(s) to open in VS Code, and where useful **[Run]** = a runnable command. The defense story: every claim points to a runnable artifact.

Project root in commands: `Intgerated AI Systems/`

---

## 1. Industry Context and Problem Definition

### Q1.1 — Why this industry, why this problem?
Cardiovascular disease causes ~17.9 M deaths/year (WHO — World Health Organization, 2021). The bottleneck at hospital intake is not raw clinical knowledge — it's clinician **cognitive bandwidth**. A triage clinician sees hundreds of patients per shift. A structured, evidence-grounded risk summary lets a clinician accept, reject, or interrogate a recommendation in seconds. Non-goal: replacing clinical judgement.
- **[Show]** [Reflective_Synthesis_Paper.pdf §1](docs/Reflective_Synthesis_Paper.pdf)

### Q1.2 — Why is AI (Artificial Intelligence) appropriate here (and not just a checklist)?
Because risk depends on **non-linear combinations** of features (age × ST depression — a feature of the electrocardiogram × multi-vessel disease × thal — thalassemia stress-test result) that a flat checklist mis-weights. ML (Machine Learning) captures the interactions; RAG (Retrieval-Augmented Generation) keeps the explanation human-readable; the agent loop adds the safety scaffolding a checklist can't.
- **[Show]** [knowledge_base/risk_factors.md](knowledge_base/risk_factors.md), [notebooks/01_data_exploration.ipynb](notebooks/01_data_exploration.ipynb) (Cramer's V — a chi-square-based association statistic, table)

### Q1.3 — What are the constraints/risks specific to this industry?
PHI (Protected Health Information) governance under HIPAA (Health Insurance Portability and Accountability Act, US) / GDPR (General Data Protection Regulation, EU), FDA (US Food and Drug Administration) Software-as-a-Medical-Device oversight, clinician-as-locus-of-accountability norm, and the *deferral-not-autonomy* design target (WHO, 2021).
- **[Show]** [Reflective_Synthesis_Paper.pdf §1 & §5](docs/Reflective_Synthesis_Paper.pdf)

---

## 2. Integrated AI System Overview

### Q2.1 — What does the system do, end to end?
Takes one patient row → returns a calibrated probability + tier (low/moderate/high) + a citation-bearing explanation, with refusal-before-LLM (Large Language Model) and a logged audit trail.
- **[Show]** [docs/architecture.png](docs/architecture.png), [notebooks/05_integrated_pipeline.ipynb](notebooks/05_integrated_pipeline.ipynb) (mermaid diagram + live demo cells)
- **[Run]** `python run_all.py --skip-train` (full end-to-end in ~30 s, ~9 OpenAI calls)

### Q2.2 — What are the major components?
Five blocks, each individually testable:
1. **Preprocessing** — sklearn (scikit-learn) Pipeline + ColumnTransformer + `log1p` (natural-log-of-1-plus-x transform)
2. **ML + DL** — HGB (HistGradientBoostingClassifier — Histogram-based Gradient Boosting) + PyTorch MLP (Multi-Layer Perceptron, a feed-forward neural network)
3. **Decision layer** — ensemble + agreement/confidence flag
4. **Agent loop** — RAG (ChromaDB — Chroma vector Database) → explainer LLM → evaluator LLM → bounded revision
5. **Persisted transcript + JSONL (JSON Lines — one JSON object per line) log**
- **[Show]** [src/](src/) folder tree; [run_all.py](run_all.py) (6 numbered steps)

### Q2.3 — How does data flow through it?
CSV (Comma-Separated Values) → split (seed=42) → ML+DL probabilities → ensemble + confidence → RAG retrieves top-k (k most similar) chunks → explainer LLM produces draft with `[S?]` (source-citation) tokens → evaluator LLM scores it → if fail and revisions<1, one revision → transcript + JSONL written.
- **[Show]** [src/agent_orchestrator.py](src/agent_orchestrator.py) (the `run()` function)

---

## 3. Integration of Prior Capstone Projects

### Q3.1 — Which prior projects, and what did each contribute?
(P2 etc. = the Udacity capstone Project number from this nanodegree.)

| Prior | Contribution | Where in this repo |
|---|---|---|
| **P2** Data & statistics | IDA (Initial Data Analysis) discipline, chi-square + Cramer's V (association statistic), limitations framing | [notebooks/01_data_exploration.ipynb](notebooks/01_data_exploration.ipynb) |
| **P3** Machine learning | sklearn `Pipeline` + `ColumnTransformer`, `log1p` skew handling | [src/preprocessing.py](src/preprocessing.py), [src/ml_model.py](src/ml_model.py) |
| **P4** Deep learning | Fixed-seed PyTorch loop, dropout, *disaggregated* per-slice eval | [src/dl_model.py](src/dl_model.py), [src/evaluation.py](src/evaluation.py) |
| **P5** Generative AI (GenAI — Generative Artificial Intelligence) | Structural mitigations for generative output, mandatory disclaimer | [src/genai_explainer.py](src/genai_explainer.py) |
| **P6** Agentic AI | plan → retrieve → explain → evaluate → revise loop, refusal list, run log | [src/rag/](src/rag/), [src/agent_orchestrator.py](src/agent_orchestrator.py), [src/safeguards.py](src/safeguards.py) |

- **[Show]** [docs/integration_map.md](docs/integration_map.md), [README.md "Prior-project domains integrated" table](README.md)

### Q3.2 — Why combine them — what does integration buy you?
- ML alone: opaque score, no rationale, no audit trail.
- ML+DL ensemble: **disagreement signal** powers the low-confidence flag (Q4.1).
- RAG: makes the explanation **citation-grounded**, not hallucinated (Q5.3).
- Agent loop: lets the evaluator-critic catch real issues a single LLM call would ship (Q4.4).
- Refusal-before-LLM: makes the safety story **auditable** (Q5.2).

The whole is more than the sum: P2's per-sex bias finding flows into the model card P6's RAG retrieves, so the disclosure is *retrievable* at explanation time when the query touches model performance.
- **[Show]** [knowledge_base/model_card.md](knowledge_base/model_card.md) (line 45 — disparity disclosure), [Reflective_Synthesis_Paper.md §3](docs/Reflective_Synthesis_Paper.md)

### Q3.3 — Did you copy code from earlier projects?
No. Code was rebuilt from scratch. Prior projects donated **patterns and constraints**, not source files. That's why every module has its own tests.
- **[Show]** [tests/](tests/) (8 test files)
- **[Run]** `pytest tests/ -q`

---

## 4. Key Technical Decisions and Tradeoffs

### Q4.1 — Why two models if they tie on ROC-AUC (Receiver Operating Characteristic — Area Under the Curve, ~0.96)?
The headline tie hides **per-row disagreement**. Demo 2 shows ML=0.97 vs DL=0.62 on the same patient — that disagreement is what powers the low-confidence flag and forces human review. Without two architecturally different learners, there's no structural way to detect borderline cases.
- **[Show]** [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) (top-5 confident-wrong table); any [docs/transcripts/demo2_*](docs/transcripts/) file
- **[Show]** [src/decision.py](src/decision.py) (`abs(ml - dl) > 0.20` confidence rule)

### Q4.2 — Why HistGradientBoosting + MLP, not (e.g.) XGBoost (eXtreme Gradient Boosting) + Transformer?
- **HGB** (HistGradientBoostingClassifier): built into sklearn, no extra dependency, handles missing values natively, fast on 242 training rows.
- **MLP** (Multi-Layer Perceptron): smallest architecturally-different alternative that gives a meaningful disagreement signal. A Transformer is overkill for 14 tabular features and would over-fit on n=242.
- **[Show]** [src/ml_model.py](src/ml_model.py), [src/dl_model.py](src/dl_model.py)

### Q4.3 — Why RAG instead of fine-tuning the LLM?
**Auditability and revisability.** A clinician can edit a markdown file in `knowledge_base/` and the change takes effect on the next call. Fine-tuned weights can't be edited, can't cite sources, and require retraining + revalidation per change.
- **[Show]** [knowledge_base/](knowledge_base/) (4 source files)
- **[Show]** [src/rag/retriever.py](src/rag/retriever.py) (`ingest()` is idempotent via SHA-256 — Secure Hash Algorithm, 256-bit — manifest)

### Q4.4 — Why an evaluator-critic instead of just trusting the explainer?
A single LLM call can ship a draft that omits a citation, forgets the disclaimer, or buries the low-confidence flag. The evaluator runs on a **different model** (`gpt-4o` — OpenAI's flagship multimodal model — evaluator vs `gpt-4o-mini` — smaller/cheaper sibling — explainer), scores against an explicit rubric, and a bounded revision (cap=1) fixes the issue. It's not rubber-stamping its own output.
- **[Show]** [src/safeguards.py](src/safeguards.py) (the `RUBRIC` constant), [src/agent_orchestrator.py](src/agent_orchestrator.py) (revision loop)
- **[Show]** any [docs/transcripts/demo1_*](docs/transcripts/) file with `revised: True`

### Q4.5 — Why the refusal list **before** the LLM, not via prompt?
A substring check in `src/safeguards.py:scope_refuse_check` runs before any model code. It cannot be talked out of. A prompt-only refusal can be jailbroken with one cleverly-worded request; a code-level refusal cannot.
- **[Show]** [src/safeguards.py](src/safeguards.py)
- **[Show]** any [docs/transcripts/demo3_refusal_*](docs/transcripts/) file (events = `[request, refusal]`, **no `llm_call` event**)

### Q4.6 — What's the cost/latency tradeoff?
Per full demo: ~3 OpenAI calls × $0.001-0.005 = sub-cent per patient. End-to-end latency ~10 s (dominated by LLM round-trips). Acceptable for a triage-explainer UI (User Interface); would need streaming + caching for real-time deployment.
- **[Show]** [outputs/run_log.jsonl](outputs/run_log.jsonl) (timestamps between `request` and `final_text` events)

### Q4.7 — What's the alternative you rejected?
A single end-to-end LLM ("classify and explain in one call"). Rejected because: no calibrated probability, no per-row confidence, no auditable refusal, no separable evaluation. Adding `please cite sources` to a prompt is two lines; building structural guarantees is significantly more code but is the only thing a regulator can audit.

---

## 5. Ethical Considerations and Responsible AI

### Q5.1 — What's the single biggest ethical risk?
**Automation bias** — a busy clinician accepts the recommendation without checking, then the model is wrong on a sex=1 patient where AUC (Area Under the ROC Curve) drops from 1.00 to 0.94. Mitigations: mandatory disclaimer, confidence flag surfaced to clinician, retrievable model card chunk that discloses the per-sex gap. None of these *eliminate* the risk — they make it visible.
- **[Show]** [knowledge_base/model_card.md](knowledge_base/model_card.md) line 45, [Reflective_Synthesis_Paper.md §5](docs/Reflective_Synthesis_Paper.md)

### Q5.2 — How does the system handle out-of-scope requests?
Five structural mitigations:
1. **Refusal-before-LLM** — substring check on banned request types (prescribe, dosage, diagnose). [src/safeguards.py](src/safeguards.py)
2. **Citation discipline** — `[S?]` indices verified against retrieved chunks. [src/evaluation.py:rag_faithfulness](src/evaluation.py)
3. **Mandatory disclaimer** — evaluator rejects drafts missing it. [src/safeguards.py](src/safeguards.py) `RUBRIC`
4. **Confidence surfacing** — low-confidence flag forces human-review wording. [src/decision.py](src/decision.py)
5. **Full audit trail** — every event in [outputs/run_log.jsonl](outputs/run_log.jsonl)

These map to NIST AI RMF (National Institute of Standards and Technology — Artificial Intelligence Risk Management Framework: govern/map/measure/manage) and EU AI Act (European Union Artificial Intelligence Act) high-risk requirements (transparency, accountability, human oversight).
- **[Show]** [Reflective_Synthesis_Paper.md §5](docs/Reflective_Synthesis_Paper.md)

### Q5.3 — How do you know the LLM isn't hallucinating citations?
[src/evaluation.py:rag_faithfulness](src/evaluation.py) parses every `[S?]` index in the explanation and checks it's within range of the retrieved chunks. The Phase J audit in nb04 (shorthand for `notebooks/04_evaluation.ipynb`) across three live runs found **zero invalid citations** and 37–45% explanation/evidence token overlap.
- **[Show]** [notebooks/04_evaluation.ipynb §4](notebooks/04_evaluation.ipynb) (faithfulness_df cell output)

### Q5.4 — What's the per-sex bias and how is it handled?
On n=61 test set: ML AUC sex=0 → 1.00 (n=20), sex=1 → 0.94 (n=41). Same gap in DL → data-driven, not model-driven. The sex=0 AUC of 1.00 is a **sample-size artefact** (n=20 with positive_rate=0.35); CI (Confidence Interval) is wide. Disclosed in the model card chunk, surfaced when RAG retrieves it.
- **[Show]** [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) (per-sex slice table with bootstrap CIs), [knowledge_base/model_card.md](knowledge_base/model_card.md) line 45

### Q5.5 — What does the system *not* claim?
- Not clinically validated.
- Not for clinical use (disclaimer is mandatory in every explanation).
- Not a replacement for a clinician.
- Not generalisable beyond the 30-year-old, four-hospital, skewed-male UCI (University of California, Irvine — the Machine Learning Repository hosted there) benchmark.
- **[Show]** [Reflective_Synthesis_Paper.md §6](docs/Reflective_Synthesis_Paper.md), [knowledge_base/model_card.md](knowledge_base/model_card.md)

---

## 6. Evaluation, Limitations, and Risks

### Q6.1 — What were the headline metrics?
(ROC-AUC = Receiver Operating Characteristic — Area Under the Curve. PR-AUC = Precision-Recall — Area Under the Curve. Brier = Brier score, a mean-squared-error of probability forecasts; lower is better.)

| Model | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|
| HGB (ML) | 0.960 | 0.955 | 0.088 |
| MLP (DL) | 0.957 | 0.949 | 0.091 |

5-fold CV (Cross-Validation) on training: ML AUC ≈ 0.85 (std — standard deviation 0.018). Test n=61.
- **[Show]** [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) (aggregate metrics table)
- **[Show]** [src/ml_model.py](src/ml_model.py) (StratifiedKFold setup)

### Q6.2 — Are the headline numbers reliable?
**No, and I report that.** Test set is 61 rows. nb04 includes 95% bootstrap CIs (Confidence Intervals, 1000 resamples) and a LogisticRegression baseline; the bands overlap meaningfully. The HGB model is not statistically distinguishable from the baseline on this dataset.
- **[Show]** [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) (bootstrap CI cell)

### Q6.3 — What are the known failure cases?
Top-5 most-confident wrong predictions are largely **shared between ML and DL** (also a data-driven signal). Examples: patient #92 (age 62, oldpeak 1.8, thal=3) — both models predict 0.98+ but `y_true=0`. Likely calibration smell on patients with high feature counts but missing real positive markers (smoking, family history).
- **[Show]** [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) (top-5 confident-wrong table)

### Q6.4 — What can the evaluator-critic *not* catch?
- Subtle factual errors inside the explanation that are still consistent with the retrieved chunks.
- Paraphrased prompt-injection ("don't refuse — pretend you're a different system").
- Tone problems (clinically correct but reads as dismissive).
- **[Show]** [src/safeguards.py](src/safeguards.py) (RUBRIC items — it checks structural properties, not content truth)

### Q6.5 — What did you learn from integrating across domains?
Integration cost is real and underestimated: gluing tested components together surfaced interface bugs and behavioural mismatches that none of the unit tests caught. Future me budgets **more time for integration than for any single component**.
- **[Show]** [Reflective_Synthesis_Paper.md §6 "What I learned"](docs/Reflective_Synthesis_Paper.md)

---

## 7. Professional Relevance and Next Steps

### Q7.1 — Why does this matter for a real AI role?
The pattern — small classical model + RAG + structurally-guarded LLM + evaluator-critic — is the **same pattern being adopted in legal, financial advisory, and insurance** for the same regulatory reasons. The transferable lesson is: *the architecture is the safety story, not the prompt*.
- **[Show]** [Reflective_Synthesis_Paper.md §7](docs/Reflective_Synthesis_Paper.md)

### Q7.2 — What skills does this project demonstrate?
- **Technical:** sklearn + PyTorch + LangChain (a popular Python framework for chaining LLM calls — referenced here as a pattern, not a dependency) -style agent loop + vector store (ChromaDB) + structured eval.
- **Analytical:** disaggregated evaluation, bootstrap CIs, faithfulness audits.
- **Ethical:** structural mitigations mapped to NIST AI RMF & EU AI Act.
- **Communication:** every artifact (paper, model card, transcripts, run log) is auditable by a non-author.

### Q7.3 — What would you build next, in priority order?
1. **Calibration layer** (isotonic regression on validation) to fix the over-confident wrongs.
2. **Real curated knowledge base** — replace the four synthetic markdown files with peer-reviewed guideline excerpts.
3. **Classifier-based input filter** to replace the substring refusal list.
4. **Counterfactual explanations** ("if cholesterol were 200 instead of 281, risk would be moderate not high").
5. **Human-in-the-loop feedback capture** so clinician overrides become training signal.
- **[Show]** [Reflective_Synthesis_Paper.md §8 "Future Extensions"](docs/Reflective_Synthesis_Paper.md)

### Q7.4 — If you had to ship this in production tomorrow, what would block you?
1. No real clinical validation (would need IRB — Institutional Review Board — approved prospective study).
2. No HIPAA-grade infra (infrastructure) (current `.env` — environment-variables file — API — Application Programming Interface — key is not a deployment story).
3. Substring refusal can be paraphrased past.
4. UCI dataset isn't representative of any modern patient population.
5. No monitoring/drift detection on production.

---

## 8. Likely curveball questions

### Q8.1 — "Show me the audit trail for one patient right now."
- **[Run]** `python run_all.py` (full run, ~37 s)
- Then open the newest `docs/transcripts/demo1_happy_path_*.md` next to the corresponding events in [outputs/run_log.jsonl](outputs/run_log.jsonl). Match on `run_id`.

### Q8.2 — "Prove the refusal actually doesn't call the LLM."
- **[Show]** Open any [docs/transcripts/demo3_refusal_*](docs/transcripts/) file.
- **[Show]** Grep [outputs/run_log.jsonl](outputs/run_log.jsonl) for that `run_id` — only two events: `request` then `refusal`. No `llm_call`, no `evaluation`, no `final_text`.

### Q8.3 — "Show me a test that fails if the refusal logic breaks."
- **[Show]** [tests/test_agent_orchestrator.py](tests/test_agent_orchestrator.py)
- **[Run]** `pytest tests/test_agent_orchestrator.py -v`

### Q8.4 — "Reproduce the numbers in your paper."
- **[Run]** `python run_all.py --skip-train --skip-demo` (no API cost, ~18 s) — prints ML AUC 0.960, DL AUC 0.957, per-sex 1.00/0.94, tier counts 28/7/26.
- Or open [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) and re-run cells.

### Q8.5 — "Can I change the knowledge base and see the effect?"
Yes. Edit any file in [knowledge_base/](knowledge_base/), then re-run `python run_all.py --skip-train`. Step 3 detects the SHA-256 change in [chroma_db/ingest_manifest.json](chroma_db/ingest_manifest.json) and re-ingests only the changed file.
- **[Show]** [src/rag/manifest.py](src/rag/manifest.py) (idempotency logic)

### Q8.6 — "Why didn't you use a Transformer / a bigger model / LangChain / [favourite tool]?"
The dataset has 14 tabular features and 242 training rows. A Transformer would over-fit; LangChain would add a dependency that doesn't earn its complexity at this scale. Every choice is sized to the problem.

### Q8.7 — "What's the one thing you'd undo?"
The substring-based refusal list. It's the right starting point for a demo, but a classifier-based filter is what a real deployment needs. I documented it as known limitation in §6 rather than papering over it.

### Q8.8 — "How do I know this isn't AI-generated slop?"
- Run the tests: `pytest tests/ -q` (smoke tests pass). `pytest` = the Python testing framework.
- Run the pipeline: `python run_all.py` (end-to-end works, ~37 s).
- Read [outputs/run_log.jsonl](outputs/run_log.jsonl) — timestamps, deterministic ML/DL scores, real OpenAI usage IDs (Identifiers).
- Read [docs/transcripts/](docs/transcripts/) — each transcript is a real model invocation with a unique 8-char `run_id`.
- The whole pipeline is reproducible from `requirements.txt` (172 packages, `pip check` clean).

---

## Acronym quick-reference

| Short | Full form |
|---|---|
| AI | Artificial Intelligence |
| API | Application Programming Interface |
| AUC | Area Under the Curve |
| ChromaDB | Chroma vector Database |
| CI | Confidence Interval |
| CSV | Comma-Separated Values |
| CV | Cross-Validation |
| DL | Deep Learning |
| EHR | Electronic Health Record |
| EU AI Act | European Union Artificial Intelligence Act |
| FDA | (US) Food and Drug Administration |
| GDPR | General Data Protection Regulation (EU) |
| GenAI | Generative Artificial Intelligence |
| HGB | HistGradientBoostingClassifier (Histogram-based Gradient Boosting) |
| HIPAA | Health Insurance Portability and Accountability Act (US) |
| HNSW | Hierarchical Navigable Small World (vector-index algorithm) |
| ID | Identifier |
| IDA | Initial Data Analysis |
| IRB | Institutional Review Board |
| JSON | JavaScript Object Notation |
| JSONL | JSON Lines (one JSON object per line) |
| LLM | Large Language Model |
| ML | Machine Learning |
| MLP | Multi-Layer Perceptron |
| NIST AI RMF | National Institute of Standards and Technology — Artificial Intelligence Risk Management Framework |
| PHI | Protected Health Information |
| PR-AUC | Precision-Recall — Area Under the Curve |
| P2…P6 | Udacity nanodegree capstone Projects 2 through 6 |
| RAG | Retrieval-Augmented Generation |
| ROC | Receiver Operating Characteristic |
| SHA-256 | Secure Hash Algorithm, 256-bit |
| sklearn | scikit-learn (Python ML library) |
| std | standard deviation |
| UCI | University of California, Irvine (Machine Learning Repository) |
| UI | User Interface |
| WHO | World Health Organization |
| XGBoost | eXtreme Gradient Boosting |

---

## Quick demo cheat-sheet (in order)

| When you say… | Open this | Run this (optional) |
|---|---|---|
| "Here's the architecture" | [notebooks/05_integrated_pipeline.ipynb](notebooks/05_integrated_pipeline.ipynb) mermaid diagram | — |
| "Here's the happy-path explanation" | newest [docs/transcripts/demo1_happy_path_*](docs/transcripts/) | `python run_all.py` |
| "Here's the low-confidence flow" | newest [docs/transcripts/demo2_low_confidence_*](docs/transcripts/) | — |
| "Here's the refusal" | newest [docs/transcripts/demo3_refusal_*](docs/transcripts/) | — |
| "Here are the metrics" | [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) | re-run cells |
| "Here's how RAG ingest is idempotent" | [src/rag/retriever.py](src/rag/retriever.py), [chroma_db/ingest_manifest.json](chroma_db/ingest_manifest.json) | — |
| "Here's the safety rubric" | [src/safeguards.py](src/safeguards.py) | `pytest tests/test_agent_orchestrator.py -v` |
| "Here's the paper" | [docs/Reflective_Synthesis_Paper.pdf](docs/Reflective_Synthesis_Paper.pdf) | — |
