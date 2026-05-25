# Reflective Synthesis Paper

**Integrative Industry Synthesis — Clinical Triage and Risk Decision Support**
**Author:** Naunihal Singh Sidhu
**Capstone integrative artifact (educational only — not for clinical use).**

---

## 1. Industry context

Cardiovascular disease (CVD) remains the leading global cause of death — roughly 17.9 million deaths a year, almost a third of all deaths worldwide (WHO, 2021a). A large fraction are downstream of a small set of modifiable risk factors — hypertension, dyslipidaemia, smoking, diabetes, obesity — whose population-level contribution is documented in the Global Burden of Disease analysis (Roth et al., 2020). Many also occur in patients who enter the healthcare system but are not triaged with the urgency their underlying risk warrants. The bottleneck is bedside cognitive bandwidth: clinicians at the front door see hundreds of patients a shift, and mis-prioritising one is asymmetric — a missed acute coronary case is catastrophic, an over-investigated low-risk patient merely inefficient.

AI in healthcare also faces sector-specific constraints: protected health information governance, FDA oversight of clinical decision support as Software as a Medical Device (U.S. FDA, 2021), and the clinician-as-locus-of-accountability norm that makes deferral, not autonomy, the design target (WHO, 2021b). The opportunity is not to replace clinical judgement but to surface a structured, evidence-grounded summary of risk a clinician can accept, reject, or interrogate in seconds. The system is a clinical-triage explainer that takes a single patient's tabular features, returns a calibrated probability, retrieves supporting evidence from a small clinical knowledge base, and produces a citation-bearing explanation under explicit guardrails.

## 2. Overview of the integrated solution

The system runs end-to-end as follows:

1. A patient row from the UCI Heart Disease dataset (Janosi et al., 1988) is preprocessed (numeric `log1p` + `StandardScaler`, categorical one-hot).
2. Two independent classifiers — a scikit-learn `HistGradientBoostingClassifier` and a PyTorch MLP — each return a probability of CVD.
3. An ensemble decision layer averages the two probabilities into a tier (`low`/`moderate`/`high`) and flags `confidence=low` when the two models disagree by more than 0.20.
4. An agent orchestrator implements a plan → retrieve → explain → evaluate → revise loop. It first checks the user request against a refusal substring list, then retrieves the top-k evidence chunks from a ChromaDB vector store of clinician-authored markdown, then asks an OpenAI chat model to draft an explanation grounded *only* in those chunks. A second LLM call acts as evaluator/critic against an explicit rubric; if the draft fails, one bounded revision is permitted.
5. Every event of every run is appended to `outputs/run_log.jsonl`, and a human-readable transcript is persisted to `docs/transcripts/`.

End-to-end behaviour is demonstrated in `notebooks/05_integrated_pipeline.ipynb` and quantitatively evaluated in `notebooks/04_evaluation.ipynb`. The full flow is depicted in Figure 1 (`docs/architecture.png`).

## 3. Integration of prior projects

The rubric for the Integrated AI System capstone requires integration of at least three prior capstones — concepts and patterns, not copy-pasted code. I rebuilt every component from scratch and used five prior projects as design lineage rather than as code donors.

| Prior project | Concept reused | Where it lives in this system |
|---|---|---|
| **P2 — Data and Statistical Reasoning** | Initial Data Analysis discipline; chi-square / Cramer's V; explicit limitations and bias section | `notebooks/01_data_exploration.ipynb`, the limitations sections of every component |
| **P3 — Machine Learning (RFM clustering)** | scikit-learn `Pipeline` + `ColumnTransformer`; `log1p` for skewed numerics; per-slice metric reporting | `src/preprocessing.py`, `src/ml_model.py` |
| **P4 — Deep Learning (CNN with dropout)** | Fixed-seed PyTorch training loop, dropout regularisation, *disaggregated* per-slice evaluation rather than headline accuracy | `src/dl_model.py`, slice tables in `src/evaluation.py` |
| **P5 — Generative AI (VAE)** | Generative-output domain; the lesson that generative models need *structural* mitigations, not prompt pleas: under-claim capability, mandatory disclaimer, citation-only grounding. The LLM explainer is itself a generative model; P5's discipline shapes how it is constrained. | `src/genai_explainer.py` |
| **P6 — Agentic AI (research-brief agent)** | Plan → retrieve → synthesise → evaluate → revise loop; ChromaDB + OpenAI embeddings; INSUFFICIENT EVIDENCE escape valve; substring refusal list; runtime caps; sha256 ingest manifest; JSONL run log | `src/rag/`, `src/agent_orchestrator.py`, `src/safeguards.py` |

These projects chain. P3's HGB and P4's MLP feed P6's ensemble; the disagreement flag is what makes P5's explainer call for human review on borderline cases. P2's per-sex bias finding from both ML and DL is written into the model card chunk available to P6's RAG, so the disclosure is retrievable at explanation time when the user query touches model performance.

## 4. Technical design decisions and tradeoffs

**Two models, not one.** A single classifier would have been simpler. I ensembled an HGB and an MLP because disagreement between two architecturally different learners is itself information: when both heads agree, the prediction is structurally more trustworthy; when they disagree, the system surfaces "human review recommended" instead of pretending the average is meaningful. The two models tied on the held-out test (ROC-AUC 0.960 each), but per-row probabilities differ enough for the disagreement flag to fire on borderline patients (demo 2 in `notebooks/05_integrated_pipeline.ipynb`).

**RAG over fine-tuning.** Fine-tuning on cardiology text would have been more impressive on paper and far less defensible in practice — fine-tuned weights cannot be audited, revised without retraining, or cite their sources. RAG against a small markdown KB lets clinicians edit a single file and have the change take effect on the next call, with sha256-based idempotent re-ingest (`src/rag/manifest.py`).

**Evaluator-critic, not just a single LLM call.** A second LLM call evaluates the draft against an explicit rubric (`src/safeguards.py:RUBRIC`) and returns structured JSON. In the integrated demo it caught real issues — missing citations, unsurfaced low-confidence — and the bounded one-shot revision corrected them. It is not a guarantee of safety but a measurable second line of defence whose verdict is logged.

**Structural refusal before the LLM.** The substring refusal list (`prescribe`, `dosage`, `diagnose me`, `legal advice`, …) short-circuits the pipeline before any expensive call. A prompt-only policy can be jailbroken; a hardcoded substring check cannot. Demo 3 demonstrates this with `refused=True` and `events=[request, refusal]` — no model call was made.

**Tradeoffs accepted.** The substring list refuses some legitimate paraphrases. The evaluator is itself an LLM and can mis-score. The KB is tiny (four files, 29 chunks). The dataset is small (n=303, test n=61). Each is documented in the model card and limitations.

## 5. Ethical, governance, and responsible-AI considerations

The system has been built with explicit, *structural* mitigations rather than prompt-level pleas. A short audit:

- **Scope refusal at the input layer.** Banned request types never reach the LLM, regardless of phrasing.
- **Citation discipline at the output layer.** The explanation prompt enforces five hard rules including verbatim score quoting and `[S?]` citations. The Phase J faithfulness check in nb04 across three live runs found *zero invalid citations* and 37–45% explanation/evidence token overlap.
- **Mandatory disclaimer.** Every non-refusal explanation ends with "Educational artifact only. Not for clinical use. The clinician is the locus of accountability."
- **Confidence surfacing.** When ML and DL disagree, the explanation explicitly recommends human review.
- **Audit trail.** Every step of every run is persisted to `outputs/run_log.jsonl` and to a human-readable transcript.
- **Disaggregated evaluation, disclosed.** The per-sex AUC gap (sex=0 → 1.00, sex=1 → 0.94 for ML; similar for DL) is reported in nb04 and surfaced in the retrieved model card.

These map directly onto the NIST AI Risk Management Framework's "govern / map / measure / manage" function categories (NIST, 2023) and onto the "transparency", "accountability" and "human oversight" requirements that the EU AI Act classifies as load-bearing for high-risk medical use cases (European Parliament, 2024).

## 6. Evaluation and Reflection

The system did meet its stated goal: a citation-bearing, refusal-aware triage explainer with a persisted audit trail, evaluated quantitatively in nb04 and end-to-end in nb05. The integration also surfaced limits worth naming:

- **Dataset.** UCI Heart Disease is small (303 rows), thirty years old, from four hospitals, and skewed male. Headline metrics on the 61-row test set are reported with 95% bootstrap CIs (1000 resamples) in nb04 alongside a plain LogisticRegression baseline, and the bands are wide enough that the gradient-boosting model overlaps the baseline. The system has no claim to clinical validity outside this benchmark.
- **Calibration.** Brier scores are good (≤0.09) but top failure-case analysis showed both models being most confident exactly when wrong on a handful of rows. The ensemble disagreement flag is the only structural mitigation.
- **Generative drift.** The LLM is a closed-weights API; OpenAI can change weights at any time. The evaluator-critic is the mitigation, but it is also an LLM and shares the failure mode.
- **Adversarial input.** The refusal list is a substring check; users can paraphrase past it. The system is gated behind a clinician; a stronger classifier-based input filter would be required for direct deployment.
- **Knowledge base.** The KB is intentionally tiny and is not a substitute for an up-to-date guideline corpus (e.g. ACC/AHA, ESC). A curated, versioned, refreshed evidence base is a precondition for any non-educational use.
- **Multiple comparisons.** nb01 reports a Bonferroni-corrected chi-square p-value, but per-slice AUCs in nb04 are point estimates without family-wise correction. They are exploratory: small-n slices (sex=0 has ~20 rows) are noisy, and the sex=0 AUC of 1.00 is a sample-size artefact.

## 7. Professional and industry relevance

The architectural pattern — a small, well-evaluated classical model plus a small RAG layer plus a structurally-guarded LLM explainer plus an evaluator-critic loop — is being adopted across regulated industries beyond healthcare (legal, finance, insurance). The reason is regulatory convergence on "the model output must be auditable, the evidence cite-able, the human the locus of accountability" (NIST, 2023; European Parliament, 2024). A monolithic LLM cannot meet that bar; the multi-stage decomposition built here can. The transferable lesson: *the architecture is the safety story* — prompt-only safety does not survive contact with regulators or adversarial users.

## 8. Future extensions

Future work includes a calibration layer (Platt or isotonic) on top of the ensemble probability, per-slice bootstrap CIs on every subgroup metric, a versioned real-guideline KB ingested via the existing manifest, a multi-arm refusal classifier to replace the substring list, counterfactual explanations from the SHAP/DiCE family, and a human-in-the-loop feedback hook so the evaluator rubric refines empirically.

## 9. Conclusion

The integrated system meets the rubric's letter — five prior projects integrated, RAG + agent loop + ensemble + per-slice evaluation + structural safety — but the point is the discipline behind the integration. Every component was rebuilt under one set of constraints (auditability, citation, refusal-before-LLM, run logging), each demonstrated with a persisted transcript. The lesson from integrating across domains: safety is an architectural property, not a prompt; each prior project contributed less a technique than a constraint the integrated system had to honour. An industry-pattern AI system is not a single brilliant model but a set of small, individually-testable components whose composition produces behaviour a regulator can sign off on.

---

## References

- European Parliament. (2024). *Regulation (EU) 2024/1689 of the European Parliament and of the Council laying down harmonised rules on artificial intelligence (Artificial Intelligence Act).* Official Journal of the European Union. https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- Janosi, A., Steinbrunn, W., Pfisterer, M., & Detrano, R. (1988). *Heart Disease* [Data set]. UCI Machine Learning Repository. https://doi.org/10.24432/C52P4X
- National Institute of Standards and Technology. (2023). *Artificial Intelligence Risk Management Framework (AI RMF 1.0)* (NIST AI 100-1). U.S. Department of Commerce. https://doi.org/10.6028/NIST.AI.100-1
- Roth, G. A., Mensah, G. A., Johnson, C. O., Addolorato, G., Ammirati, E., Baddour, L. M., … Fuster, V. (2020). Global burden of cardiovascular diseases and risk factors, 1990–2019: Update from the GBD 2019 study. *Journal of the American College of Cardiology*, 76(25), 2982–3021. https://doi.org/10.1016/j.jacc.2020.11.010
- U.S. Food and Drug Administration. (2021). *Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a Medical Device (SaMD) Action Plan.* https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-and-machine-learning-software-medical-device
- World Health Organization. (2021a). *Cardiovascular diseases (CVDs) — fact sheet.* https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds)
- World Health Organization. (2021b). *Ethics and governance of artificial intelligence for health: WHO guidance.* https://www.who.int/publications/i/item/9789240029200
