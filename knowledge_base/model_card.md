# Model Card — Clinical Triage Risk Models

This card describes the ML (Machine Learning) and DL (Deep Learning) components of the integrated triage system. It is retrieved by the agent at explanation time so that any score quoted in a patient summary can be traced back to a known, documented model.

## Intended use

- **Primary use:** educational artifact for the Udacity AI Mastery Capstone (Project 7).
- **Out of scope:** clinical decision-making, diagnosis, treatment recommendation, triage routing in production, any patient-facing deployment.
- **Audience:** course mentors, reviewers, and the author.

## Models

### ML (Machine Learning) risk model

- **Algorithm:** scikit-learn `HistGradientBoostingClassifier` (300 iterations, learning rate 0.05).
- **Preprocessing:** median imputation → `log1p` → `StandardScaler` for numeric features; mode imputation → one-hot encoding for categorical features.
- **Training data:** UCI (University of California, Irvine) Heart Disease (Cleveland + Hungarian + Switzerland + VA (Veterans Affairs) Long Beach), 80% training split, stratified on the binary `target`.
- **Headline metrics:** 5-fold CV (cross-validation) ROC-AUC (Receiver Operating Characteristic Area Under the Curve) ≈ 0.85, test ROC-AUC ≈ 0.96 on this small held-out split.
- **Persisted to:** `models/ml_model.joblib` (not committed).

### DL (Deep Learning) risk model

- **Architecture:** PyTorch MLP (Multi-Layer Perceptron), two hidden layers of 64 units with ReLU (Rectified Linear Unit) + Dropout(0.3), single logit output.
- **Optimization:** Adam (lr = 1e-3, weight decay = 1e-4), BCE (Binary Cross-Entropy)-with-logits loss, batch size 32, 80 epochs, fixed seed 42, CPU only.
- **Same preprocessing pipeline** as the ML model (`log1p` + `StandardScaler` on numerics, one-hot on categoricals).
- **Headline metrics:** test ROC-AUC ≈ 0.96, PR-AUC (Precision-Recall Area Under the Curve) ≈ 0.95, Brier ≈ 0.09.
- **Persisted to:** `models/dl_model.pt` (not committed).

## Decision layer

- Ensemble probability = mean of ML (Machine Learning) and DL (Deep Learning) probabilities (50/50 by default).
- Risk tiers on the ensemble probability: **low** < 0.30, **moderate** 0.30–0.70, **high** ≥ 0.70.
- A **low-confidence flag** is set when |ml_prob − dl_prob| > 0.20. In low-confidence cases the agent is required to defer / surface uncertainty rather than commit to a tier.

## Known limitations

- **Small, biased cohort.** ~300 records, skewed male and older. Per-slice metrics by sex and age band reveal AUC (Area Under the Curve) differences that are point estimates on tiny slices.
- **Feature availability.** Several inputs (`ca`, `thal`, `oldpeak`, `slope`) are post-workup variables; the model implicitly assumes they are present at scoring time. A production system would have to split feature sets by acquisition cost.
- **Missing variables.** Smoking, family history, BMI (Body Mass Index), HbA1c (glycated hemoglobin), LDL (low-density lipoprotein) / HDL (high-density lipoprotein), medications — all absent.
- **No temporal validity.** The dataset reflects a single historical window; concept drift is not assessed.

## Bias and fairness

- The cohort skews male and older. Slice metrics by `sex` and age band are reported in `notebooks/02_ml_risk_model.ipynb` and `notebooks/03_dl_risk_model.ipynb`.
- The same per-sex AUC gap appears in both ML (Machine Learning) and DL (Deep Learning) — evidence the disparity is data-driven, not model-driven.

## Responsible-use posture

- Patient explanations produced by the GenAI (Generative AI) layer must be grounded in retrieved evidence and quote the model scores verbatim. If retrieval is empty or evidence is insufficient, the system returns `INSUFFICIENT EVIDENCE` rather than fabricating a narrative.
- Trained weights are **not** redistributed. Anyone wishing to reproduce the models must re-run training on their own machine.
- A "not for clinical use" disclaimer is rendered with every explanation.

## Versioning

- Project version: 0.1 (Phase F).
- Data version: UCI Heart Disease (ID 45), original 1988 collection, retrieved via `ucimlrepo`.
