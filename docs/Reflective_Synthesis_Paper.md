# Reflective Synthesis Paper

**Integrative Industry Synthesis — Clinical Triage and Risk Decision Support**
**Author:** Naunihal Singh Sidhu
**Capstone integrative artifact (educational only — not for clinical use).**

---

## 1. Industry context

Cardiovascular disease (CVD) remains the leading global cause of death, accounting for roughly 17.9 million deaths a year and almost a third of all deaths worldwide (World Health Organization, 2021). A large fraction of these events are downstream of a small set of modifiable risk factors — hypertension, dyslipidaemia, smoking, diabetes, obesity — and a large fraction occur in patients who *did* enter the healthcare system but were not triaged with the urgency their underlying risk warranted (Roth et al., 2020). The bottleneck is not raw clinical knowledge; it is bedside cognitive bandwidth. Clinicians at the front door of a hospital see hundreds of patients a shift, and the cost of mis-prioritising one is asymmetric: a missed acute coronary case is catastrophic, an over-investigated low-risk patient is merely inefficient.

This is the context in which I situated my Integrated AI System capstone. The opportunity here is not to replace clinical judgement (neither legal nor ethical) but to surface a structured, evidence-grounded summary of risk a clinician can accept, reject, or interrogate within seconds. The system is a clinical-triage explainer that takes a single patient's tabular features, returns a calibrated probability, retrieves supporting evidence from a small clinical knowledge base, and produces a citation-bearing English explanation under explicit guardrails.

## 2. Overview of the integrated solution

The system runs end-to-end as follows:

1. A patient row from the UCI Heart Disease dataset (Janosi et al., 1988) is preprocessed (numeric `log1p` + `StandardScaler`, categorical one-hot).
2. Two independent classifiers — a scikit-learn `HistGradientBoostingClassifier` and a PyTorch MLP — each return a probability of CVD.
3. An ensemble decision layer averages the two probabilities into a tier (`low`/`moderate`/`high`) and flags `confidence=low` when the two models disagree by more than 0.20.
4. An agent orchestrator implements a plan → retrieve → explain → evaluate → revise loop. It first checks the user request against a refusal substring list, then retrieves the top-k evidence chunks from a ChromaDB vector store of clinician-authored markdown, then asks an OpenAI chat model to draft an explanation grounded *only* in those chunks. A second LLM call acts as evaluator/critic against an explicit rubric; if the draft fails, one bounded revision is permitted.
5. Every event of every run is appended to `outputs/run_log.jsonl`, and a human-readable transcript is persisted to `docs/transcripts/`.

End-to-end behaviour is demonstrated in `notebooks/05_integrated_pipeline.ipynb` and quantitatively evaluated in `notebooks/04_evaluation.ipynb`.

## 3. Integration of prior projects

The rubric for the Integrated AI System capstone requires integration of at least three prior capstones — concepts and patterns, not copy-pasted code. I rebuilt every component from scratch and used five prior projects as design lineage rather than as code donors.

| Prior project | Concept reused | Where it lives in this system |
|---|---|---|
| **P2 — Data and Statistical Reasoning** | Initial Data Analysis discipline; chi-square / Cramer's V; explicit limitations and bias section | `notebooks/01_data_exploration.ipynb`, the limitations sections of every component |
| **P3 — Machine Learning (RFM clustering)** | scikit-learn `Pipeline` + `ColumnTransformer`; `log1p` for skewed numerics; per-slice metric reporting | `src/preprocessing.py`, `src/ml_model.py` |
| **P4 — Deep Learning (CNN with dropout)** | Fixed-seed PyTorch training loop, dropout regularisation, *disaggregated* per-slice evaluation rather than headline accuracy | `src/dl_model.py`, slice tables in `src/evaluation.py` |
| **P5 — Generative AI (VAE)** | Responsible-framing of generative output: under-claim capability, structural mitigations baked into the prompt, mandatory disclaimer as the final line | `src/genai_explainer.py` |
| **P6 — Agentic AI (research-brief agent)** | Plan → retrieve → synthesise → evaluate → revise loop; ChromaDB + OpenAI embeddings; INSUFFICIENT EVIDENCE escape valve; substring refusal list; runtime caps; sha256 ingest manifest; JSONL run log | `src/rag/`, `src/agent_orchestrator.py`, `src/safeguards.py` |

Critically, the integration is not stylistic; the same per-sex performance gap that appeared in both ML and DL is acknowledged in the model card retrieved at explanation time, so the disclosure surfaces in the actual explanation a clinician would read.

## 4. Technical design decisions and tradeoffs

**Two models, not one.** A single classifier would have been simpler. I deliberately ensembled an HGB and an MLP because the disagreement signal between two architecturally different learners is itself information: when both heads agree, the prediction is structurally more trustworthy than either alone; when they disagree, the system surfaces "human review recommended" instead of pretending the average is meaningful. On the held-out test set the two models tied almost exactly (ROC-AUC 0.960 each), but their per-row probabilities differ enough to make the disagreement flag fire on real borderline patients (demo 2 in `notebooks/05_integrated_pipeline.ipynb`).

**RAG over fine-tuning.** Fine-tuning a model on cardiology text would have been more impressive on paper and far less defensible in practice — fine-tuned weights cannot be audited, cannot be revised without retraining, and cannot cite their sources. RAG against a small markdown knowledge base lets clinicians edit a single file and have the change take effect on the next call, with sha256-based idempotent re-ingest (`src/rag/manifest.py`).

**Evaluator-critic, not just a single LLM call.** A second LLM call evaluates the draft against an explicit rubric (`src/safeguards.py:RUBRIC`) and returns structured JSON. In the integrated demo it caught real issues — missing inline citations, low-confidence not surfaced explicitly — and the bounded one-shot revision corrected them (visible in demo 2's transcript). The evaluator is not a guarantee of safety, but it is a measurable second line of defence whose verdict is logged.

**Structural refusal before the LLM, not just in the prompt.** The substring refusal list (`prescribe`, `dosage`, `diagnose me`, `legal advice`, …) short-circuits the pipeline before any expensive call. A prompt-only safety policy can be jailbroken; a hardcoded substring check on the user request cannot. Demo 3 demonstrates this with `refused=True` and `events=[request, refusal]` — no model call was made.

**Tradeoffs accepted.** The substring list will refuse legitimate paraphrases (false-positive rate >0). The evaluator is itself an LLM and can mis-score. The KB is tiny (four markdown files, 29 chunks). The dataset is small (n=303, test n=61). Each of these is an honest engineering tradeoff documented in the model card and limitations sections rather than glossed over.

## 5. Ethical, governance, and responsible-AI considerations

The system has been built end-to-end with explicit, *structural* mitigations rather than prompt-level pleas. A short audit:

- **Scope refusal at the input layer.** Banned request types never reach the LLM, regardless of phrasing nuance.
- **Citation discipline at the output layer.** The explanation prompt enforces five hard rules including verbatim score quoting and `[S?]` citations to the retrieved evidence. The Phase J faithfulness check across three live runs found *zero invalid citations* and 36–44% explanation/evidence token overlap.
- **Mandatory disclaimer.** Every non-refusal explanation ends with "Educational artifact only. Not for clinical use. The clinician is the locus of accountability for any decision."
- **Confidence surfacing.** When ML and DL disagree, the explanation explicitly recommends human review.
- **Audit trail.** Every step of every run is persisted to `outputs/run_log.jsonl` and to a human-readable transcript.
- **Disaggregated evaluation, disclosed.** The per-sex AUC gap (sex=0 → 1.00, sex=1 → 0.94 for ML; very similar for DL) is reported in `notebooks/04_evaluation.ipynb` and surfaced in the retrieved model card — a clinician asking the system about a female patient sees the model card text.

These map directly onto the NIST AI Risk Management Framework's "govern / map / measure / manage" function categories (NIST, 2023) and onto the "transparency", "accountability" and "human oversight" requirements that the EU AI Act classifies as load-bearing for high-risk medical use cases (European Parliament, 2024).

## 6. Limitations and risks

- **Dataset.** UCI Heart Disease is small (303 rows), thirty years old, drawn from four hospitals, and skewed male. Headline metrics on the 61-row test set are reported with 95% bootstrap CIs (1000 resamples) in nb04 alongside a plain LogisticRegression baseline, and the bands are wide enough that the gradient-boosting model overlaps the baseline. The system therefore has no claim to clinical validity outside this benchmark.
- **Calibration.** The Brier scores are good (≤0.09) but the top failure-case analysis showed both models being most confident exactly when they were wrong on a handful of rows. The ensemble disagreement flag is the only structural mitigation.
- **Generative drift.** The LLM is a closed-weights API; OpenAI can change the underlying weights at any time. The mitigation is the evaluator-critic, not the LLM itself, but the evaluator is also an LLM and shares the failure mode.
- **Adversarial input.** The refusal list is a substring check; an adversarial user can paraphrase past it. The mitigation is that the system is gated behind a clinician — it is not deployed to patients directly — but in a real deployment a stronger classifier-based input filter would be required.
- **Knowledge base.** The KB is intentionally tiny and is not a substitute for an up-to-date guideline corpus (e.g. ACC/AHA, ESC). Replacing the four-file KB with a curated, versioned, regularly refreshed evidence base is a precondition for any non-educational use.

## 7. Professional and industry relevance

The architectural pattern here — a small, well-evaluated classical model plus a small RAG layer plus a structurally-guarded LLM explainer plus an evaluator-critic loop — is the same pattern currently being adopted across regulated industries beyond healthcare (legal, financial advisory, insurance). The reason is regulatory: regulators are converging on "the model output must be auditable, the evidence must be cite-able, the human must remain the locus of accountability" (NIST, 2023; European Parliament, 2024). A monolithic LLM cannot meet that bar; the multi-stage decomposition built here can. The transferable lesson: *the architecture is the safety story* — prompt-only safety does not survive contact with regulators or adversarial users.

## 8. Future extensions

- **Calibration layer** (Platt scaling or isotonic regression) on top of the ensemble probability before tier assignment.
- **Bootstrap confidence intervals** on every reported metric in `notebooks/04_evaluation.ipynb`.
- **Real KB.** Replace the four-file synthetic KB with a versioned snapshot of a real guideline corpus, ingested via the existing sha256 manifest.
- **Multi-arm refusal classifier** to replace the substring list, reducing false positives on legitimate paraphrases.
- **Counterfactual explanation.** Surface the smallest feature change that would move the patient out of the high tier, drawing on the SHAP / DiCE family of methods.
- **Human-in-the-loop feedback capture.** Append clinician accept/reject + free-text feedback to the run log so the evaluator rubric can be refined empirically.

## 9. Conclusion

The integrated system meets the rubric's letter — five prior projects integrated, RAG + agent loop + ensemble + per-slice evaluation + structural safety — but the more important point is the discipline behind the integration. Every component was rebuilt from scratch under a single set of constraints (auditability, citation, refusal-before-LLM, run logging), and every constraint was demonstrated with a live, persisted transcript. That is the form an industry-pattern AI system has to take when it is deployed inside a regulated workflow: not a single brilliant model, but a set of small, individually-testable components whose composition produces a behaviour a regulator can sign off on.

---

## References

- European Parliament. (2024). *Regulation (EU) 2024/1689 of the European Parliament and of the Council laying down harmonised rules on artificial intelligence (Artificial Intelligence Act).* Official Journal of the European Union.
- Janosi, A., Steinbrunn, W., Pfisterer, M., & Detrano, R. (1988). *Heart Disease* [Data set]. UCI Machine Learning Repository. https://doi.org/10.24432/C52P4X
- National Institute of Standards and Technology. (2023). *Artificial Intelligence Risk Management Framework (AI RMF 1.0)* (NIST AI 100-1). U.S. Department of Commerce.
- Roth, G. A., Mensah, G. A., Johnson, C. O., Addolorato, G., Ammirati, E., Baddour, L. M., … Fuster, V. (2020). Global burden of cardiovascular diseases and risk factors, 1990–2019: Update from the GBD 2019 study. *Journal of the American College of Cardiology*, 76(25), 2982–3021. https://doi.org/10.1016/j.jacc.2020.11.010
- World Health Organization. (2021). *Cardiovascular diseases (CVDs) — fact sheet.* https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds)
