# Integration Map — Prior Capstone Projects → Clinical Triage System

This project integrates methods and design rationale from five prior capstone projects. Code is **rebuilt** for this submission to keep the artifact independently runnable; what is reused is *patterns, design discipline, and lessons learned*. Each module in `src/` carries a short header attributing its lineage.

| # | Prior Project | Methods / Insights Adapted | Where in this system |
|---|---|---|---|
| **P2** | Data & Statistical Reasoning — UCI Bank Marketing, chi-square test of independence | Structured Initial Data Analysis before modeling; chi-square + Cramer's V for categorical association; explicit Limitations & Bias framing (selection bias, leakage caveats) | `notebooks/01_data_exploration.ipynb`; paper §Industry Context & §Limitations |
| **P3** | Machine Learning — UCI Online Retail II, K-Means RFM segmentation | `log1p` + `StandardScaler` pipeline for skewed numeric features; scikit-learn `Pipeline` / `ColumnTransformer`; reporting cluster/cohort sizes alongside metrics; PCA(2) for interpretable visualization | `src/preprocessing.py`, `src/ml_model.py`, integrated notebook visualization |
| **P4** | Deep Learning — Fashion-MNIST CNN with dropout regularization | PyTorch training loop with fixed seed; dropout; per-class / per-slice disaggregated evaluation (the "non-uniform error redistribution" insight); CPU-budget honesty in reporting | `src/dl_model.py`; `src/evaluation.py` (bias audit by sex / age band) |
| **P5** | Generative AI — Convolutional VAE on CIFAR-10 vehicles | Responsible-AI framing for generative outputs: structural mitigations baked into design choices; "synthesis without provenance" risk; under-claiming model capability; no model-weight redistribution | `src/genai_explainer.py` guardrails; paper §Ethics (design-choice → mitigation table) |
| **P6** | Agentic AI — Research Brief Agent (plan + RAG + evaluator) | Plan → Route → Synthesise → Evaluate → Revise loop; specialised prompt-pattern agents; Chroma + OpenAI `text-embedding-3-small` RAG; tool registry; `INSUFFICIENT EVIDENCE` escape valve; refusal list; runtime caps; sha256 ingest manifest; JSONL run log | `src/rag/`, `src/agent_orchestrator.py`, `outputs/run_log.jsonl` |

## What is new in this project

- Industry context: clinical triage / cardiovascular risk decision support.
- Dataset: UCI Heart Disease (supervised binary classification on tabular data).
- Cross-domain integration: ML + DL + RAG + GenAI + agentic orchestration in one workflow.
- Healthcare-specific responsible-AI analysis: bias slices, hallucination mitigation via grounding, human-in-the-loop gating, "not for clinical use" disclaimers.

## What is explicitly *not* reused

- No prior-project source code is copied or vendored.
- Datasets from prior projects (Bank Marketing, Online Retail II, Fashion-MNIST, CIFAR-10) are not used here.
- Prior model weights are not reused.
