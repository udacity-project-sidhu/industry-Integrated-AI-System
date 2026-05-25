# Defense FAQ v2 — Deep Defense Edition (Project 8)

This is the **long-form** version of [Defense_FAQ.md](Defense_FAQ.md). It's written for a reviewer who suspects an AI did all the work and will probe with **basic-concept questions**, ask to **show the code**, and ask to **show the cell output**.

For every question I give:

- **What it means** (concept, in plain words; no acronyms left unexplained)
- **How it's implemented here** (file + function + key line)
- **What output to point at** (notebook cell or transcript or log line)
- **What I'd say in my own words** if pressed

All paths are relative to `Intgerated AI Systems/` (yes, the folder has a typo — that's the original commit and I left it).

> **Worked example used throughout this doc.** To make every "before/after" concrete, every transform section below shows what happens to **the same real patient** — the first row of the deterministic test set (`seed=42`). The full step-by-step trace lives in [§17 Worked example](#17-worked-example--one-real-row-through-every-step), but the key before/after also appears in each transform's own Q&A so you can grasp the effect without scrolling. The numbers are not made up — they were captured live from the project's venv; you can re-run the script in §17.17 and get them back bit-for-bit.
>
> **The reference patient — traceable to source**:
> - **pandas index**: `219` (i.e. `df.iloc[219]`)
> - **CSV row**: line **221** of [data/raw/heart_disease.csv](data/raw/heart_disease.csv) (header on line 1, data row 220 → file line 221)
> - **How to recover**: `df = load_heart_disease(); df.iloc[219]` or `sp.X_test.iloc[[0]]` after `split_and_preprocess(df)` with `seed=42`
> - **Raw CSV line**: `59,1,4,138,271,0,2,182,0,0.0,1,0.0,3.0,0,0`
>
> **The reference patient (raw row, as a record)**:
>
> | age | sex | cp | trestbps | chol | fbs | restecg | thalach | exang | oldpeak | slope | ca | thal | num | target (=`y_true`) |
> |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
> | 59 | 1 | 4 | 138 | 271 | 0 | 2 | 182 | 0 | 0.0 | 1 | 0.0 | 3.0 | 0 | **0** |

> Acronym shorthand used throughout — every term is expanded at first use AND in the [glossary at the bottom](#acronym--term-glossary). If you ever forget one, scroll there.

---

## Table of contents

1. [Industry context and problem definition](#1-industry-context-and-problem-definition)
2. [System overview and architecture](#2-system-overview-and-architecture)
3. [Data — what it is, how it flows](#3-data--what-it-is-how-it-flows)
4. [Preprocessing — what each transform does and why](#4-preprocessing--what-each-transform-does-and-why)
5. [Machine Learning model (HGB) — concept + code](#5-machine-learning-model-hgb--concept--code)
6. [Deep Learning model (MLP) — concept + code](#6-deep-learning-model-mlp--concept--code)
7. [Decision layer — ensemble + tier + confidence](#7-decision-layer--ensemble--tier--confidence)
8. [Retrieval-Augmented Generation (RAG)](#8-retrieval-augmented-generation-rag)
9. [The agent loop — explainer + evaluator + revision](#9-the-agent-loop--explainer--evaluator--revision)
10. [Safety, refusal, and disclaimer](#10-safety-refusal-and-disclaimer)
11. [Evaluation — metrics, slicing, faithfulness](#11-evaluation--metrics-slicing-faithfulness)
12. [Notebook walkthrough (cell-by-cell, where outputs live)](#12-notebook-walkthrough)
13. [Tests — what they prove](#13-tests--what-they-prove)
14. [Reproducibility, environment, and runtime](#14-reproducibility-environment-and-runtime)
15. [Ethics, limitations, professional relevance](#15-ethics-limitations-professional-relevance)
16. [Cross-examination drills (the gotcha questions)](#16-cross-examination-drills)
17. [Worked example — one real row through every step](#17-worked-example--one-real-row-through-every-step)
18. [Acronym & term glossary](#acronym--term-glossary)

---

## 1. Industry context and problem definition

### Q1.1 — In plain words, what does this system do?
It takes one patient's clinical row, returns a numeric risk score for coronary artery disease (CAD — narrowing of the heart's blood vessels), classifies it into low / moderate / high risk, and writes a short clinician-readable explanation that cites the guideline lines it leaned on. It is a **decision-support** tool: a clinician still owns the final decision.

- **[Show code]** [run_all.py](run_all.py) lines 120–145 (Step 6/6 — three live agent demos).
- **[Show output]** Any [docs/transcripts/demo1_happy_path_*.md](docs/transcripts/) — a complete end-to-end record of one patient.

### Q1.2 — Why healthcare, why heart disease?
Cardiovascular disease (heart and blood-vessel disease) causes ~17.9 million deaths per year (World Health Organization (WHO), 2021). The hospital intake step is bandwidth-limited — a triage clinician sees hundreds of patients per shift. An explainable score saves seconds of mental load per patient, which adds up.

- **[Show]** [docs/Reflective_Synthesis_Paper.pdf §1](docs/Reflective_Synthesis_Paper.pdf).

### Q1.3 — What regulations would this fall under in production?
- **HIPAA** (Health Insurance Portability and Accountability Act, US) — controls how Protected Health Information (PHI — any data that identifies a patient combined with health facts) is handled.
- **GDPR** (General Data Protection Regulation, EU) — broader personal-data law; medical data is "special category".
- **US FDA** (Food and Drug Administration) **Software as a Medical Device (SaMD)** — clinical-decision software needs validation if it influences care.
- **EU AI Act** — classifies medical AI as **high-risk**, requiring transparency, human oversight, and risk management.
- **NIST AI RMF** (National Institute of Standards and Technology — Artificial Intelligence Risk Management Framework) — the US voluntary framework (govern/map/measure/manage) I mapped my mitigations against.

- **[Show]** [docs/Reflective_Synthesis_Paper.md §5](docs/Reflective_Synthesis_Paper.md).

### Q1.4 — Why not just a printed checklist for the clinician?
Because risk depends on **non-linear interactions** — e.g. age × ST depression (a feature on the electrocardiogram (ECG — recording of heart electrical activity)) × number of major vessels coloured by fluoroscopy × thalassemia stress-test result. A flat additive checklist mis-weights interactions. A learned model captures them; an explanation makes them human-readable.

---

## 2. System overview and architecture

### Q2.1 — Walk me through the architecture in one breath.
One patient row → preprocess → score with two different models (HGB + MLP) → ensemble + confidence flag → safety check (refuse if request is out-of-scope) → retrieve top-k guideline chunks via RAG → explainer LLM drafts an explanation with `[S1]/[S2]` citations → evaluator LLM checks against a rubric → if it fails, ONE bounded revision → write transcript + append every event to a JSON-Lines audit log.

- **[Show diagram]** [docs/architecture.png](docs/architecture.png) and the Mermaid source in [notebooks/05_integrated_pipeline.ipynb](notebooks/05_integrated_pipeline.ipynb) (cell 3).
- **[Show code]** [src/agent_orchestrator.py](src/agent_orchestrator.py) — the `run()` function around line 156 is the spine.

### Q2.2 — What are the major components, in files?

| Component | File | Key symbol |
|---|---|---|
| Preprocessing | [src/preprocessing.py](src/preprocessing.py) | `build_preprocessor()` ~L39, `split_and_preprocess()` ~L62 |
| ML model | [src/ml_model.py](src/ml_model.py) | `build_model()` ~L40, `train_and_evaluate()` ~L57 |
| DL model | [src/dl_model.py](src/dl_model.py) | `MLPClassifier` ~L40, `train_and_evaluate()` ~L70 |
| Decision | [src/decision.py](src/decision.py) | `score_patient()` ~L54, `score_cohort()` ~L86 |
| Safeguards | [src/safeguards.py](src/safeguards.py) | `REFUSAL_SUBSTRINGS` ~L14, `is_refused()` ~L57, `RUBRIC` ~L46 |
| RAG ingest | [src/rag/retriever.py](src/rag/retriever.py) | `ingest()` ~L14, `search()` ~L45 |
| Chunking | [src/rag/knowledge_base.py](src/rag/knowledge_base.py) | `chunk_markdown()` ~L67 |
| Vector store | [src/rag/vector_store.py](src/rag/vector_store.py) | `get_collection()` ~L24, `query()` ~L54 |
| Manifest | [src/rag/manifest.py](src/rag/manifest.py) | `changed_files()` ~L35 |
| Explainer LLM | [src/genai_explainer.py](src/genai_explainer.py) | `explain()` ~L99, `SYSTEM_PROMPT` ~L36 |
| Orchestrator | [src/agent_orchestrator.py](src/agent_orchestrator.py) | `run()` ~L156 |
| Transcript writer | [src/transcripts.py](src/transcripts.py) | `save_transcript()` ~L11 |
| Config | [src/config.py](src/config.py) | `Settings` ~L15, singleton `settings` ~L30 |
| Evaluation | [src/evaluation.py](src/evaluation.py) | `aggregate_metrics()` ~L38, `rag_faithfulness()` ~L115 |

### Q2.3 — Why split into so many files? Couldn't this be one script?
Each block has its **own unit test** in [tests/](tests/). If a regulator asks "show me the test that proves your refusal works", I open [test_agent_orchestrator.py](tests/test_agent_orchestrator.py) and run `pytest -k refusal`. A monolithic script would couple all behaviours and make targeted testing impossible.

---

## 3. Data — what it is, how it flows

### Q3.1 — What is the dataset?
The **UCI Heart Disease** dataset (University of California, Irvine Machine Learning Repository). 303 rows, 14 columns. The target column `num` is 0 (no disease) or 1–4 (disease present, severity); we **binarise** it to 0/1 (`> 0` → 1).

- **[Show code]** [src/data_loader.py](src/data_loader.py) — `load_heart_disease()` fetches it and writes a single Comma-Separated-Values (CSV) file to [data/raw/heart_disease.csv](data/raw/heart_disease.csv).
- **[Show output]** [notebooks/01_data_exploration.ipynb](notebooks/01_data_exploration.ipynb) cell 4 — `df.shape` should print `(303, 14)`.

### Q3.2 — What does each feature mean?
See [knowledge_base/feature_dictionary.md](knowledge_base/feature_dictionary.md). Short tour:

| Column | Type | Meaning (in plain words) |
|---|---|---|
| `age` | numeric | Age in years |
| `sex` | categorical | 1 = male, 0 = female |
| `cp` | categorical | Chest-pain type (1–4) |
| `trestbps` | numeric | Resting systolic blood pressure (millimetres of mercury, mmHg) |
| `chol` | numeric | Serum cholesterol (milligrams per decilitre, mg/dL) |
| `fbs` | categorical | Fasting blood sugar > 120 mg/dL (1/0) |
| `restecg` | categorical | Resting ECG result (0/1/2) |
| `thalach` | numeric | Maximum heart rate achieved during exercise |
| `exang` | categorical | Exercise-induced chest pain (1/0) |
| `oldpeak` | numeric | ST-segment depression on ECG induced by exercise |
| `slope` | categorical | Slope of the peak exercise ST segment |
| `ca` | categorical | Number of major vessels coloured by fluoroscopy (0–3) |
| `thal` | categorical | Thalassemia (a blood disorder; 3/6/7 in original encoding) |
| `num` | target | 0 = no disease, 1–4 = disease (binarised here) |

### Q3.3 — Why was the train/test split made deterministic with `seed=42`?
A **seed** fixes the pseudo-random shuffling so the train/test split is bit-identical on every run. This is what makes the same patient end up in the test set every time, and the same patient end up as "demo1" every time. Without it, demo selection would drift across runs and reviewers couldn't reproduce my numbers.

- **[Show code]** [src/preprocessing.py](src/preprocessing.py) — `RANDOM_STATE = 42` ~L27.
- **[Show]** [src/dl_model.py](src/dl_model.py) — `set_seed()` ~L32 fixes Python, NumPy, and PyTorch RNGs (random-number generators) for the deep-learning side.

### Q3.4 — How big is the test set, really?
20% of 303 rows ≈ **61 rows**. That is small. I report it everywhere and add bootstrap confidence intervals (CIs — see Q11.3) so reviewers see the uncertainty bands.

---

## 4. Preprocessing — what each transform does and why

### Q4.1 — What does `log1p` do and why apply it?
`log1p(x) = ln(1 + x)` (natural logarithm of `1 + x`). It compresses the **right tail** of right-skewed features (e.g. `chol`, `oldpeak`). The `+1` makes it safe at `x = 0`. After `log1p`, the histogram looks more bell-shaped, which helps any model that assumes roughly-symmetric inputs.

**Row-view on our reference patient `df.iloc[219]`** (numeric columns only):

Before:

| | age | trestbps | chol | thalach | oldpeak |
|---|---|---|---|---|---|
| `df.iloc[219]` | 59.0 | 138.0 | 271.0 | 182.0 | 0.0 |

After `log1p`:

| | age | trestbps | chol | thalach | oldpeak |
|---|---|---|---|---|---|
| `df.iloc[219]` | 4.0943 | 4.9345 | 5.6058 | 5.2095 | 0.0000 |

**Column-view (per-feature derivation)**:

| Feature | Before | After `log1p` | Calculation |
|---|---|---|---|
| `age` | 59.0 | 4.0943 | `ln(60)` |
| `trestbps` | 138.0 | 4.9345 | `ln(139)` |
| `chol` | 271.0 | 5.6058 | `ln(272)` |
| `thalach` | 182.0 | 5.2095 | `ln(183)` |
| `oldpeak` | 0.0 | 0.0000 | `ln(1)` — the `+1` saves us from `ln(0) = -∞` |

- **[Show code]** [src/preprocessing.py](src/preprocessing.py) — inside `build_preprocessor()` ~L39, the numeric branch is `Imputer(median) → log1p → StandardScaler`.

### Q4.2 — What does `StandardScaler` do?
Subtracts the column mean and divides by the column standard deviation, so each numeric feature has mean 0 and standard deviation 1. Neural networks train more stably on standardised inputs; tree models like HGB don't strictly need it but it doesn't hurt.

**Row-view on `df.iloc[219]`** (continuing from `log1p` output). The fitted scaler holds:
```
mean_  = [4.0035, 4.8739, 5.504,  5.0046, 0.558 ]
scale_ = [0.1687, 0.1301, 0.2029, 0.1618, 0.5064]
```

Before (input to scaler = output of `log1p`):

| | age | trestbps | chol | thalach | oldpeak |
|---|---|---|---|---|---|
| `df.iloc[219]` | 4.0943 | 4.9345 | 5.6058 | 5.2095 | 0.0000 |

After `StandardScaler`:

| | age | trestbps | chol | thalach | oldpeak |
|---|---|---|---|---|---|
| `df.iloc[219]` | 0.5386 | 0.4656 | 0.5017 | 1.2658 | −1.1020 |

**Column-view (per-feature derivation)**:

| Feature | After `log1p` | (value − mean) | / scale | **After scale** |
|---|---|---|---|---|
| `age` | 4.0943 | 0.0908 | / 0.1687 | **0.5386** |
| `trestbps` | 4.9345 | 0.0606 | / 0.1301 | **0.4656** |
| `chol` | 5.6058 | 0.1018 | / 0.2029 | **0.5017** |
| `thalach` | 5.2095 | 0.2049 | / 0.1618 | **1.2658** |
| `oldpeak` | 0.0000 | −0.5580 | / 0.5064 | **−1.1020** |

Read the output as "how many train-set standard deviations above/below the mean". This patient's `thalach` is +1.27 σ (high), `oldpeak` is −1.10 σ (low).

### Q4.3 — What does `OneHotEncoder` do?
Turns a categorical column with K values into K binary columns (one "1" per row). It avoids the trap of treating `cp = 4` as "four times bigger than `cp = 1`" — chest-pain types are labels, not magnitudes.

**Row-view on `df.iloc[219]`** (8 categorical columns → 23 binary columns):

Before (8 categorical fields):

| | sex | cp | fbs | restecg | exang | slope | ca | thal |
|---|---|---|---|---|---|---|---|---|
| `df.iloc[219]` | 1 | 4 | 0 | 2 | 0 | 1 | 0 | 3 |

After (23 binary fields, group-coloured for readability):

| | sex_0 | sex_1 | cp_1 | cp_2 | cp_3 | cp_4 | fbs_0 | fbs_1 | restecg_0 | restecg_1 | restecg_2 | exang_0 | exang_1 | slope_1 | slope_2 | slope_3 | ca_0 | ca_1 | ca_2 | ca_3 | thal_3 | thal_6 | thal_7 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `df.iloc[219]` | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |

**Column-view (per-group derivation)**:

| Group | Raw value | Output columns | Row values |
|---|---|---|---|
| `sex` | 1 | `sex_0, sex_1` | `0, 1` |
| `cp` | 4 | `cp_1, cp_2, cp_3, cp_4` | `0, 0, 0, 1` |
| `fbs` | 0 | `fbs_0, fbs_1` | `1, 0` |
| `restecg` | 2 | `restecg_0, restecg_1, restecg_2` | `0, 0, 1` |
| `exang` | 0 | `exang_0, exang_1` | `1, 0` |
| `slope` | 1 | `slope_1, slope_2, slope_3` | `1, 0, 0` |
| `ca` | 0 | `ca_0, ca_1, ca_2, ca_3` | `1, 0, 0, 0` |
| `thal` | 3 | `thal_3, thal_6, thal_7` | `1, 0, 0` |

### Q4.4 — Why median imputation, not mean?
Median is robust to outliers. With small medical datasets, one extreme value can pull the mean far off; the median doesn't move.

**Effect on `df.iloc[219]`**: zero — this row has no missing values, so impute is a pass-through. For test rows where `ca` or `thal` was `NaN`, you'd see the **training-set median** of that column substituted in (e.g. `ca` median across the 242 training rows).

### Q4.5 — Show me the preprocessor.
[src/preprocessing.py](src/preprocessing.py) — `build_preprocessor()` returns a `sklearn.compose.ColumnTransformer` with the numeric pipeline above and the categorical pipeline `Imputer(most_frequent) → OneHotEncoder` applied to `CATEGORICAL_FEATURES`. The fitted preprocessor is then **pickled inside the ML pipeline** so loading the model also loads its preprocessing.

**Row-view on `df.iloc[219]` — final stitched output** (5 numeric + 23 categorical = 28 columns of shape `(1, 28)`):

| | age | trestbps | chol | thalach | oldpeak | sex_0 | sex_1 | cp_1 | cp_2 | cp_3 | cp_4 | fbs_0 | fbs_1 | restecg_0 | restecg_1 | restecg_2 | exang_0 | exang_1 | slope_1 | slope_2 | slope_3 | ca_0 | ca_1 | ca_2 | ca_3 | thal_3 | thal_6 | thal_7 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `df.iloc[219]` | 0.5386 | 0.4656 | 0.5017 | 1.2658 | −1.1020 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |

**Column-view (concise)**:
```
[0.5386, 0.4656, 0.5017, 1.2658, -1.1020,    # numeric (scaled log1p)
 0, 1,                                         # sex
 0, 0, 0, 1,                                   # cp
 1, 0,                                         # fbs
 0, 0, 1,                                      # restecg
 1, 0,                                         # exang
 1, 0, 0,                                      # slope
 1, 0, 0, 0,                                   # ca
 1, 0, 0]                                      # thal
```
This is exactly the input the ML and DL models see.

### Q4.6 — Where does the fitted preprocessor live?
For ML: inside [models/ml_model.joblib](models/ml_model.joblib) — the joblib file (`joblib` = Python serialization library optimized for NumPy arrays) contains both preprocessor and classifier as one `sklearn.pipeline.Pipeline`. For DL: separately in [models/dl_model_meta.pt](models/dl_model_meta.pt) alongside the input dimensionality.

---

## 5. Machine Learning model (HGB) — concept + code

### Q5.1 — What is a HistGradientBoostingClassifier (HGB)?
- **Boosting** = build many small decision trees one after another, where each tree tries to correct the errors of the previous one.
- **Gradient boosting** = the "correction" is computed using gradients of a loss function (here, log-loss for binary classification).
- **Histogram-based** = instead of considering every unique feature value, the algorithm pre-buckets feature values into ~255 bins. That makes training much faster and uses much less memory.

scikit-learn's `HistGradientBoostingClassifier` is the in-tree implementation (no external dependency like XGBoost or LightGBM needed).

### Q5.2 — Why this model on this dataset?
- 14 columns, 242 training rows. Trees are the natural fit for small, mixed tabular data.
- Handles missing values **natively** — no need for me to impute first.
- It's part of `sklearn`, so no extra dependency.

### Q5.3 — Show me the code.
[src/ml_model.py](src/ml_model.py):
- `build_model()` ~L40 — returns `Pipeline([("preprocessor", …), ("model", HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=42))])`.
- `train_and_evaluate()` ~L57 — runs 5-fold StratifiedKFold cross-validation and final test-set evaluation.

### Q5.4 — What hyperparameters did you pick and why?
- `max_iter=300` — number of boosting iterations (trees). Plenty for 242 rows.
- `learning_rate=0.05` — small step size; trades training time for stability.
- `random_state=42` — for repeatability.

I deliberately did not run an exhaustive sweep — with n=242 it would over-fit the test set faster than it would inform a real choice. I report this honestly in [docs/Reflective_Synthesis_Paper.md §6](docs/Reflective_Synthesis_Paper.md).

### Q5.5 — What's K-fold cross-validation (CV)?
Split the training set into K equal "folds". For each fold, train on the other K-1 folds and evaluate on this fold; average the K scores. **Stratified** K-fold keeps the positive-class rate similar in each fold, important on imbalanced data. Here K=5, so the CV score is the average of 5 train/evaluate cycles.

### Q5.6 — Show me the CV score.
- **[Show code]** [src/ml_model.py](src/ml_model.py) — `cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` around L63.
- **[Show output]** [notebooks/02_ml_risk_model.ipynb](notebooks/02_ml_risk_model.ipynb) — the cell that prints `MLMetrics(...)` will show `cv_roc_auc_mean ≈ 0.85`, `cv_roc_auc_std ≈ 0.018`. Also surfaced in [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) cell 5.

### Q5.7 — What does this model output for our reference patient?
Input: the 28-column vector from §Q4.5.

**Row-view** — model output for `df.iloc[219]`:

| | ml_prob | y_true |
|---|---|---|
| `df.iloc[219]` | **0.5648** | 0 |

Ground truth on this patient is `y_true = 0`, so this is the model **on the wrong side of 0.5**, but only by a hair — which is exactly why the wide "moderate" tier band exists (see §7).

---

## 6. Deep Learning model (MLP) — concept + code

### Q6.1 — What is an MLP?
A **Multi-Layer Perceptron** — the simplest kind of feed-forward neural network. "Feed-forward" means data flows in one direction with no loops. Here it has three linear layers separated by ReLU activations and Dropout regularization. The final layer outputs a single number, which becomes a probability via the sigmoid embedded in `BCEWithLogitsLoss` (binary cross-entropy with logits — combines sigmoid and binary cross-entropy in a numerically stable way).

### Q6.2 — Architecture in numbers.
`Linear(input_dim → 64) → ReLU → Dropout(0.3) → Linear(64 → 64) → ReLU → Dropout(0.3) → Linear(64 → 1)`.

- **ReLU** (Rectified Linear Unit) = `max(0, x)`. Introduces non-linearity, lets the network learn curved decision boundaries.
- **Dropout(0.3)** = during training, randomly zero out 30% of activations per step. Forces the network not to rely on any single neuron — a classic **regularization** (overfitting-prevention) trick.

### Q6.3 — Show me the code.
[src/dl_model.py](src/dl_model.py):
- `MLPClassifier` class ~L40 — the architecture above.
- `train_and_evaluate()` ~L70 — `epochs=80`, `batch_size=32`, `lr=1e-3`, `weight_decay=1e-4`, optimiser is Adam.
- `set_seed()` ~L32 — fixes Python `random`, NumPy `np.random`, and PyTorch `torch.manual_seed` so re-runs match.

### Q6.4 — Why these hyperparameters?
- `hidden_dim=64` — small enough to avoid overfitting on 242 rows.
- `dropout=0.3` — a typical mid-range value; stronger would underfit, weaker would overfit.
- `epochs=80` — enough for the loss to flatten; the training history is saved in `DLMetrics.history` so I can plot it.
- `weight_decay=1e-4` — L2 regularization (penalises large weights), another overfit guard.

### Q6.5 — What's an optimizer? What's Adam?
An **optimizer** is the algorithm that updates the model's weights to reduce the loss. Plain gradient descent uses a fixed step size. **Adam** (Adaptive Moment Estimation) keeps per-parameter running averages of past gradients and their squares, then adapts the step size for each parameter. In practice, Adam works well out-of-the-box, which is why it's the default for small MLPs.

### Q6.6 — How do you save the trained model?
PyTorch convention: save the **state dict** (a Python dict mapping layer name → weight tensor) to a `.pt` file (`.pt` = PyTorch's conventional extension for `torch.save()`). The architecture lives in code, so I reconstruct `MLPClassifier(input_dim)` and call `load_state_dict()`. Sidecar metadata (input dimensionality and the preprocessing pipeline) is saved to [models/dl_model_meta.pt](models/dl_model_meta.pt).

### Q6.7 — What does the DL model output for our reference patient?
Input: the same 28-column vector from §Q4.5. At inference, `Dropout` is a no-op (model in `.eval()` mode), so the forward pass is deterministic.

**Row-view** — model output for `df.iloc[219]`:

| | dl_prob | y_true |
|---|---|---|
| `df.iloc[219]` | **0.5558** | 0 |

Note how close it is to `ml_prob = 0.5648` — the two models **agree** here (within 0.01), which feeds the confidence rule in §7.
---

## 7. Decision layer — ensemble + tier + confidence

### Q7.1 — What does the decision layer actually do?
Given `ml_prob` and `dl_prob` for one patient, it:

1. Computes `ensemble_prob = 0.5 * ml_prob + 0.5 * dl_prob` (simple average).
2. Maps that to `tier`: `low` if `< 0.30`, `high` if `> 0.70`, otherwise `moderate`.
3. Sets `confidence = "high"` if `|ml_prob - dl_prob| <= 0.20`, else `"low"`. (Two architecturally-different models disagreeing is a structural signal of borderline-ness.)

**Row-view on `df.iloc[219]`**:

Before (inputs from §Q5.7 and §Q6.7):

| | ml_prob | dl_prob |
|---|---|---|
| `df.iloc[219]` | 0.5648 | 0.5558 |

After (decision-layer outputs):

| | ml_prob | dl_prob | ensemble_prob | tier | confidence | low_threshold | high_threshold | y_true |
|---|---|---|---|---|---|---|---|---|
| `df.iloc[219]` | 0.5648 | 0.5558 | **0.5603** | **moderate** | **high** | 0.30 | 0.70 | 0 |

**Column-view (per-quantity derivation)**:

| Quantity | Computation | Value |
|---|---|---|
| `ml_prob` | from HGB | `0.5648` |
| `dl_prob` | from MLP | `0.5558` |
| `ensemble_prob` | `0.5 * 0.5648 + 0.5 * 0.5558` | `0.5603` |
| `tier` | `0.30 ≤ 0.5603 < 0.70` → moderate | `"moderate"` |
| `\|ml − dl\|` | `\|0.5648 − 0.5558\|` | `0.009` |
| `confidence` | `0.009 ≤ 0.20` → high | `"high"` |

- **[Show code]** [src/decision.py](src/decision.py) — `score_patient()` ~L54, constants at L25/L26/L29.

### Q7.2 — Why 0.30 and 0.70, why not 0.5?
Because a wide "moderate" band **forces human review on borderline cases**. With a single 0.5 threshold, a patient at 0.51 looks identical to a patient at 0.99. Splitting low / moderate / high keeps the in-between cases visible and reviewable.

### Q7.3 — Why does disagreement matter?
HGB and MLP are *architecturally* different (trees vs. neural network). When they agree, both inductive biases point the same way — high confidence. When they disagree by more than 0.20, the patient sits on a feature-space boundary where the two model families "see" different things. That is exactly when a clinician should look harder.

- **[Show output]** [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) cell 13 — top-5 most-confident-wrong table; in [notebooks/05_integrated_pipeline.ipynb](notebooks/05_integrated_pipeline.ipynb) cell 8 the agreement rate across the cohort is printed (a single number like `agreement_rate = 0.85`).

### Q7.4 — How is the ensemble probability used downstream?
It is the number tiered into low/moderate/high. It is also written **verbatim** into the explainer's prompt (Q9.4) so the LLM cannot reword or round it.

---

## 8. Retrieval-Augmented Generation (RAG)

### Q8.1 — What is RAG, in one paragraph?
A pattern where an LLM **cannot use its parametric knowledge alone** — instead, before the LLM is called, a retriever fetches the most relevant chunks of trusted source text and the LLM is told "only cite these". It cuts hallucination risk and gives you an audit trail (you can show the user *which* source line was used).

### Q8.2 — What's the "knowledge base" here?
Four hand-written markdown files in [knowledge_base/](knowledge_base/):

- [feature_dictionary.md](knowledge_base/feature_dictionary.md) — what each input column means.
- [model_card.md](knowledge_base/model_card.md) — model metrics, limitations, per-sex bias disclosure.
- [risk_factors.md](knowledge_base/risk_factors.md) — clinical risk factors for CAD (Coronary Artery Disease).
- [triage_workflow.md](knowledge_base/triage_workflow.md) — three-tier triage and what each tier means.

### Q8.3 — How is the knowledge base prepared for retrieval?
Three stages: **chunk → embed → store**.

1. **Chunking** — split each markdown file by H1/H2 headings (header-aware), then hard-split any chunk longer than 1500 characters. Each chunk gets a SHA-256 (Secure Hash Algorithm, 256-bit) id derived from its text.
   - **[Show code]** [src/rag/knowledge_base.py](src/rag/knowledge_base.py) — `chunk_markdown()` ~L67.
2. **Embedding** — each chunk's text is sent to OpenAI's `text-embedding-3-small` model, which returns a 1536-dimensional vector that captures meaning.
   - **[Show code]** [src/rag/embeddings.py](src/rag/embeddings.py).
3. **Store** — vectors + text + metadata are persisted in ChromaDB (a local vector database), inside [chroma_db/](chroma_db/), using an HNSW (Hierarchical Navigable Small World) index for fast nearest-neighbour search.
   - **[Show code]** [src/rag/vector_store.py](src/rag/vector_store.py) — `get_collection()` ~L24, `query()` ~L54.

### Q8.4 — What is an embedding?
A numeric vector representation of a piece of text such that texts with similar meaning land **close to each other** in the vector space (close as measured by cosine similarity). Embeddings are what turn "fuzzy meaning match" into a math problem.

### Q8.5 — What does cosine similarity mean?
The cosine of the angle between two vectors. Range −1 to 1; for embeddings of natural text it's usually 0 to 1. **1.0** = exact same direction (meaning), **0** = orthogonal (unrelated), **−1** = opposite. Higher is more similar.

### Q8.6 — What is HNSW (Hierarchical Navigable Small World)?
A graph-based **approximate nearest-neighbour** (ANN) algorithm. Instead of comparing your query to every stored vector (linear time), HNSW builds a multi-layer graph of "highway" links between vectors so search can start coarse and zoom in. Logarithmic-ish search time at >95% recall. Chroma's default index.

### Q8.7 — How is re-ingestion handled? Doesn't it re-embed every time?
No — that's the point of [src/rag/manifest.py](src/rag/manifest.py). On every `ingest()` call, the manifest at [chroma_db/ingest_manifest.json](chroma_db/ingest_manifest.json) is compared against the current SHA-256 hash of each knowledge-base file. **Only changed files** are re-embedded; old chunks from those sources are deleted first.

- **[Show code]** [src/rag/manifest.py](src/rag/manifest.py) — `changed_files()` ~L35.
- **[Show output]** Run `python run_all.py --skip-train` twice in a row — Step 3 the second time prints something like `ingest_summary: {'changed_files': 0, 'chunks_added': 0}`.

### Q8.8 — How does retrieval work at query time?
[src/agent_orchestrator.py](src/agent_orchestrator.py) `_build_query()` ~L147 builds a short natural-language query from the patient's salient features (chest pain, thal, exang, oldpeak, slope, ca). That query is embedded by the same model, and `vector_store.query()` returns the top-k chunks by cosine similarity. Default `retrieval_k = 4` ([src/safeguards.py](src/safeguards.py) `RuntimeCaps` ~L34).

**Before → after example** (from real demo1 transcript [docs/transcripts/demo1_happy_path_608da255.md](docs/transcripts/demo1_happy_path_608da255.md)):

*Before* — input is a one-row DataFrame of patient features.

*Intermediate* — `_build_query()` produces this natural-language string:
```
"Cardiovascular risk explanation for cp=4.0, thal=7.0, exang=1.0,
 oldpeak=0.0, slope=1.0, ca=0.0"
```

*After* — ChromaDB returns `k=4` chunks:
```json
{
  "n_results": 4,
  "sources": ["risk_factors.md", "feature_dictionary.md",
              "risk_factors.md", "feature_dictionary.md"]
}
```
These become the `[S1]`–`[S4]` references the explainer is allowed to cite.

### Q8.9 — What if no chunk is similar enough?
Below a `SIMILARITY_FLOOR = 0.25` ([src/genai_explainer.py](src/genai_explainer.py) ~L30), the chunk is rejected. If nothing passes, the explainer returns the `INSUFFICIENT_EVIDENCE` string instead of calling the LLM. No silent guessing.

---

## 9. The agent loop — explainer + evaluator + revision

### Q9.1 — What's an "agent loop" here? It's not a generic ReAct agent.
Correct — it is a constrained, single-turn loop with one optional revision. The pattern is **plan → retrieve → explain → evaluate → (maybe) revise**. The "agentic" part is that a second LLM critiques the first LLM's output against an explicit rubric, and if the critique fails, the explainer is called once more with the critic's instructions appended.

- **[Show code]** [src/agent_orchestrator.py](src/agent_orchestrator.py) — `run()` ~L156. Read it top-to-bottom; it is one function, no magic.

### Q9.2 — Why two LLMs (`gpt-4o-mini` and `gpt-4o`)?
- `gpt-4o-mini` (OpenAI's smaller/cheaper model) is the **explainer** — does most of the work, cheap per call.
- `gpt-4o` (OpenAI's flagship) is the **evaluator** — used sparingly, but stronger reasoning on rubric compliance. Defending against the "model marking its own homework" critique: the evaluator is a **different model**, so a systematic bias in the explainer is less likely to be silently approved.

Configured in [src/config.py](src/config.py) ~L15 via `chat_model` and `evaluator_model` (overridable via environment variables `OPENAI_CHAT_MODEL` and `OPENAI_EVALUATOR_MODEL`).

### Q9.3 — Show me the explainer's prompt.
[src/genai_explainer.py](src/genai_explainer.py) ~L36 has `SYSTEM_PROMPT`. It contains five hard rules: (1) evidence-only facts, (2) mandatory `[S#]` citations, (3) verbatim numeric scores, (4) banned content (no prescriptions, no diagnoses), (5) tone/length, plus a required output structure: tier line → model-agreement note → 3–5 cited bullets → "what the system does not know" paragraph → mandatory disclaimer line.

### Q9.4 — How are the model scores passed in such that the LLM can't reword them?
[src/genai_explainer.py](src/genai_explainer.py) `_patient_block()` ~L80 formats `ml_prob`, `dl_prob`, `ensemble_prob` to three decimals as text. The system prompt says "use the scores **verbatim**". The evaluator checks for verbatim presence in the draft.

### Q9.5 — What is the evaluator looking for?
The full rubric is in [src/safeguards.py](src/safeguards.py) `RUBRIC` ~L46–56 — seven criteria covering: (a) directly addresses the question, (b) citations present and valid, (c) verbatim scores, (d) required structure, (e) no banned content, (f) uncertainty surfacing, (g) tone & length. Returns JSON: `{"pass": bool, "score": 0-10, "issues": [...], "instructions": "..."}`.

### Q9.6 — How is the revision bounded?
`max_revisions = 1` in [src/safeguards.py](src/safeguards.py) `RuntimeCaps` ~L36. If the evaluator's first pass fails, the explainer is called **once** with the critic's `instructions`. If it still fails after that, the latest draft is returned anyway and `revised = True` is logged. There is no infinite loop.

### Q9.7 — Show me a revision actually happening.
- **[Show output]** Find any [docs/transcripts/demo1_happy_path_*.md](docs/transcripts/) where the front-matter says `revised: True`. The `evaluation` section shows the issues the critic raised; the `explanation` section shows the rewritten text.

**Before → after on a real revision** (from [docs/transcripts/demo1_happy_path_608da255.md](docs/transcripts/demo1_happy_path_608da255.md), `revised: True`):

*Draft bullet (before)*:
```
- The peak exercise capacity (`thalach` = 156.0) is above the
  age-predicted maximum, which is generally favorable but should
  be considered alongside other risk factors [S3].
```

*Evaluator verdict (intermediate)*:
```json
{
  "pass": false,
  "score": 7,
  "issues": [
    "Unsupported claim about peak exercise capacity",
    "Incorrect interpretation of peak exercise capacity",
    "Missing citation for peak exercise capacity claim"
  ],
  "instructions": "Revise the explanation to remove the unsupported
   claim about peak exercise capacity being above the age-predicted
   maximum, as this is not supported by the evidence provided. ..."
}
```

*Final bullet (after revision)*:
```
- The peak exercise capacity (`thalach` = 156.0) is not explicitly
  linked to risk in the provided evidence, thus its interpretation
  should be approached with caution.
```

The unsupported claim is gone; the rewrite stays inside the retrieved evidence.

### Q9.8 — What gets logged where?
Every step appends an event to [outputs/run_log.jsonl](outputs/run_log.jsonl). One full demo logs roughly: `request → score → rag_search → draft → evaluation → (optional) revision → final_text`. The same event payload is also kept in the `events` list inside the per-demo transcript so the two views are reconcilable by `run_id`.

- **[Show code]** [src/agent_orchestrator.py](src/agent_orchestrator.py) — `_log()` ~L83.

---

## 10. Safety, refusal, and disclaimer

### Q10.1 — How does refusal work?
Before any LLM call, [src/safeguards.py](src/safeguards.py) `is_refused(request)` ~L57 does a **case-insensitive substring check** against `REFUSAL_SUBSTRINGS` ~L14 (13 banned phrases including "prescribe", "dosage", "diagnose me", "self-harm", "weapon"). If any match, the orchestrator short-circuits with `RunResult(refused=True, refusal_reason=<matched substring>)` and **never calls the LLM**.

**Before → after on the real demo3 row** (from [docs/transcripts/demo3_refusal_0e9613d5.md](docs/transcripts/demo3_refusal_0e9613d5.md)):

*Before* — user request:
```
"Prescribe a medication and dosage for this patient."
```

*Intermediate* — substring scan:
```
"prescribe" ∈ REFUSAL_SUBSTRINGS
request.lower().contains("prescribe") → True
```

*After* — short-circuit, full event log is only 2 entries:
```
- refused: True
- refusal_reason: matched refusal substring: prescribe
- revised: False
- events: [request, refusal]      # no llm_call, no draft, no evaluation
```
### Q10.2 — Why a code check and not a prompt-only refusal?
A prompt-only refusal can be jailbroken with one cleverly-worded request ("ignore your previous instructions"). A substring check in Python source cannot be talked out of by the user's text. It is the only refusal layer the user cannot reach.

### Q10.3 — Prove the LLM was not called on refusal.
- **[Show output]** Open any [docs/transcripts/demo3_refusal_*.md](docs/transcripts/). Its `events` section will show only two events: `request` and `refusal`. **No `llm_call`, no `evaluation`, no `final_text`.**
- **[Show output]** Grep [outputs/run_log.jsonl](outputs/run_log.jsonl) for that `run_id` and see only those two events.

### Q10.4 — What if a paraphrase slips past the substring filter?
Then the explainer's SYSTEM_PROMPT still bans prescription/diagnosis content, and the evaluator checks for it. But yes — substring matching is brittle. I list it as a known limitation in [docs/Reflective_Synthesis_Paper.md §6](docs/Reflective_Synthesis_Paper.md) and call for a classifier-based input filter in the future-work section.

### Q10.5 — Show me the disclaimer.
[src/genai_explainer.py](src/genai_explainer.py) ~L31 has `DISCLAIMER = "Educational artifact only. Not for clinical use. The clinician is the locus of accountability for any decision."` It is injected into every explanation, and the evaluator's rubric (item 4 — "required structure") rejects drafts that drop it.

### Q10.6 — What other structural mitigations are in place?
1. Refusal-before-LLM (Q10.1).
2. Citation discipline — `[S#]` indices verified against retrieved chunks ([src/evaluation.py](src/evaluation.py) `rag_faithfulness()` ~L115).
3. Mandatory disclaimer — evaluator rejects drafts without it.
4. Confidence surfacing — low-confidence flag forces human-review wording ([src/decision.py](src/decision.py)).
5. Full audit trail — every event in [outputs/run_log.jsonl](outputs/run_log.jsonl).

These map to NIST AI RMF (govern/map/measure/manage) and EU AI Act high-risk requirements (transparency, accountability, human oversight). See [docs/Reflective_Synthesis_Paper.md §5](docs/Reflective_Synthesis_Paper.md).

---

## 11. Evaluation — metrics, slicing, faithfulness

### Q11.1 — What metrics did you report and what do they mean?
| Metric | Plain words | Range | Where computed |
|---|---|---|---|
| **ROC-AUC** (Receiver Operating Characteristic — Area Under the Curve) | Probability the model ranks a random positive higher than a random negative. Threshold-independent. | 0.5 = random, 1.0 = perfect | [src/evaluation.py](src/evaluation.py) `aggregate_metrics()` ~L38 |
| **PR-AUC** (Precision-Recall — Area Under the Curve) | Same idea but on precision vs. recall — better for imbalanced data | 0 to 1 | same |
| **Brier score** | Mean squared error between predicted probability and actual label. Penalises over-confident wrongs. | 0 = perfect, 0.25 = random for balanced | same |
| **Accuracy @ 0.5** | Fraction correct using 0.5 cutoff | 0 to 1 | same |

### Q11.2 — Headline numbers.
| Model | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|
| HGB (ML) | 0.960 | 0.955 | 0.088 |
| MLP (DL) | 0.957 | 0.949 | 0.091 |

5-fold cross-validation on training: ML AUC ≈ 0.85 (std ≈ 0.018). Test n = 61.

- **[Show output]** [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) cell 5 prints the aggregate metrics DataFrame with these numbers.

### Q11.3 — Are those numbers reliable? It's 61 rows.
No, and I say so. Cell 6 of [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) computes 95% bootstrap **confidence intervals** (CI) on test ROC-AUC by resampling the test set 1000 times with replacement. It also computes a `LogisticRegression` baseline. The CI bands overlap meaningfully — the HGB model is **not statistically distinguishable** from the baseline on this dataset. That is in the paper too.

### Q11.4 — What's a confidence interval?
A range that, with stated probability (here 95%), would contain the true value if the experiment were repeated many times. Wide CI = high uncertainty about the point estimate. The CI on n=61 ROC-AUC is wide; that's the honest answer.

### Q11.5 — What is "disaggregated evaluation"?
Not just one global metric — separate metrics for slices of the test set (by sex, by age band, by chest-pain type). Catches bias that aggregate metrics hide.

### Q11.6 — Show me the per-sex slice.
[notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) cell 9 prints the per-sex slice table for ML and DL. Result: `sex=0 → AUC 1.00 (n=20)`, `sex=1 → AUC 0.94 (n=41)`. The same gap appears in DL, which tells me the cause is **data**, not model. Cell 10 slices by `cp` and `thal`.

### Q11.7 — Is the sex=0 AUC really 1.00?
On this 20-row slice, yes — but n=20 is tiny and the bootstrap CI on that slice is wide. I describe it as a **sample-size artefact**, not as evidence of perfect performance, in [knowledge_base/model_card.md](knowledge_base/model_card.md) line 45 and in the paper.

### Q11.8 — What is "RAG faithfulness"?
The check that the explanation **only cites evidence it was actually given**. Implemented in [src/evaluation.py](src/evaluation.py) `rag_faithfulness()` ~L115: it regex-parses every `[S#]` in the explanation (regex `CITATION_RE = r"\[S(\d+)\]"` ~L25), checks each index is within the range of retrieved chunks, and also computes the token-overlap between the explanation and the cited chunks.

### Q11.9 — Show me the faithfulness audit.
[notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) cell 16 runs three demonstration patients through the agent and prints `faithfulness_df` with columns `n_citations`, `n_unique_citations`, `n_chunks_available`, `invalid_citation_indices`, `uncited_chunks_count`, `explanation_token_overlap`. Across three live runs: **zero invalid citations**, 37–45% explanation/evidence token overlap.

### Q11.10 — What are the top failure cases?
[notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) cell 13 prints the top-5 most-confident-wrong table (sorted by `|prob - 0.5|` descending). Implemented in [src/evaluation.py](src/evaluation.py) `failure_cases()` ~L87. The top errors are **largely shared between ML and DL** — another data-driven (not model-driven) signal.

---

## 12. Notebook walkthrough

This section lists each notebook's purpose and exactly which cells produce the numbers a reviewer might ask to see.

### `01_data_exploration.ipynb` — Initial Data Analysis (IDA)
- Loads the CSV, prints shape, checks missing values, computes chi-square + Cramer's V (a chi-square-based association statistic) for categorical–target associations.
- **Key output**: associations table (which features are most correlated with the target).

### `02_ml_risk_model.ipynb` — ML training notebook
- Builds the preprocessor, trains HGB, prints `MLMetrics(cv_roc_auc_mean, cv_roc_auc_std, test_roc_auc, test_pr_auc, test_brier)`.
- **Key output**: those five numbers; saved model at [models/ml_model.joblib](models/ml_model.joblib).

### `03_dl_risk_model.ipynb` — DL training notebook
- Builds the MLP, trains 80 epochs, plots loss curve, prints `DLMetrics(test_roc_auc, test_pr_auc, test_brier, epochs, history)`.
- **Key output**: those metrics; saved weights at [models/dl_model.pt](models/dl_model.pt) and metadata at [models/dl_model_meta.pt](models/dl_model_meta.pt).

### `04_evaluation.ipynb` — The evaluation notebook (most-grilled)

| Cell | Section | Output to point at |
|---|---|---|
| 5 | §1 Aggregate metrics | AggregateMetrics DataFrame (ML + DL rows) |
| 6 | §1 (continued) | Bootstrap 95% CI on test AUC + LogisticRegression baseline |
| 9 | §2 Slice tables | Per-sex slices (ML + DL), per-age-band slices |
| 10 | §2 (continued) | Slices by `cp` and `thal` |
| 13 | §3 Top failure cases | Top-5 most-confident-wrong table |
| 16 | §4 RAG faithfulness | `faithfulness_df` for three demonstration patients |
| 18 | §5 Failure-mode summary | Synthesis callouts that flow into the paper |

### `05_integrated_pipeline.ipynb` — The live end-to-end demo notebook

| Cell | Section | Output to point at |
|---|---|---|
| 3 | Mermaid architecture diagram | Visual of the full pipeline |
| 6 | §1 Load + ingest | `ingest_summary` dict — proves idempotency on rerun |
| 8 | §2 Score cohort | `agreement_rate` + tier counts (low/moderate/high) |
| 11 | §3 Pick demos | Deterministic indices for demo1/demo2/demo3 |
| 14, 16 | §4 Demo 1 happy path | Explanation text + evaluator verdict + `revised` flag |
| 18, 20 | §5 Demo 2 low-confidence | Patient score + `confidence='low'` + uncertainty wording |
| 22 | §6 Demo 3 refusal | `refused=True`, `refusal_reason` + short event list |
| 25 | §7 Audit log | Tail of [outputs/run_log.jsonl](outputs/run_log.jsonl), filtered by `run_id` |

---

## 13. Tests — what they prove

`pytest` (the Python testing framework) discovers files matching `test_*.py`. Run all of them with `pytest tests/ -q` from the project root.

| File | What it proves |
|---|---|
| [tests/test_data_pipeline.py](tests/test_data_pipeline.py) | The CSV loads to expected shape; train/test split runs and respects the seed |
| [tests/test_ml_model.py](tests/test_ml_model.py) | HGB trains and persists; loaded model produces a valid probability |
| [tests/test_dl_model.py](tests/test_dl_model.py) | MLP trains and persists; loaded model matches saved weights |
| [tests/test_decision.py](tests/test_decision.py) | `score_patient` and `score_cohort` produce correct tiers and confidence flags |
| [tests/test_rag.py](tests/test_rag.py) | Chunking is header-aware; KB loads; end-to-end retrieve returns chunks |
| [tests/test_genai_explainer.py](tests/test_genai_explainer.py) | Refuses on empty evidence; live explanation cites valid sources |
| [tests/test_evaluation.py](tests/test_evaluation.py) | Aggregate, slice, age-bucket, top-k failures, and `rag_faithfulness` all behave |
| [tests/test_agent_orchestrator.py](tests/test_agent_orchestrator.py) | Refusal path short-circuits (no LLM call); happy-path live demo returns a full RunResult |

**[Run]** `pytest tests/ -q` — should report all tests passing (some live tests are skipped unless `OPENAI_API_KEY` is set).

---

## 14. Reproducibility, environment, and runtime

### Q14.1 — How does a reviewer reproduce this?
1. Unzip [Industry_Integrated_AI_System_Submission.zip](../Industry_Integrated_AI_System_Submission.zip).
2. `python -m venv .venv && .venv\Scripts\Activate.ps1`
3. `pip install -r requirements.txt` (172 packages, exact pin).
4. Copy `.env.example` to `.env` and paste an OpenAI API key.
5. `python run_all.py --skip-train --skip-demo` (no LLM cost, ~18 s) — proves the deterministic numbers.
6. `python run_all.py` (~37 s, ~9 OpenAI calls, sub-cent) — runs three live demos and writes three transcripts.

### Q14.2 — Why pin the requirements?
LLM behaviour drifts model-side; we cannot freeze the OpenAI endpoint. But the local pipeline (numpy, sklearn, torch, chromadb) **can** be frozen, and pinning prevents future-package drift from silently changing my numbers.

### Q14.3 — Is the pipeline deterministic end-to-end?
The numeric pipeline is — same seed, same CSV, same metrics every time. The LLM stages are not bit-deterministic (model side), but the **structure** is: same refusal verdict, same tier, same revision-flag pattern across runs.

---

## 15. Ethics, limitations, professional relevance

### Q15.1 — Biggest single risk?
**Automation bias** — a busy clinician accepts the recommendation without checking, then the model is wrong on a `sex=1` patient where ML AUC drops from 1.00 to 0.94. Mitigations (mandatory disclaimer, confidence flag, retrievable model-card disclosure) make the risk **visible**, not zero.

### Q15.2 — What does this system **not** claim?
- Not clinically validated.
- Not for clinical use.
- Not a replacement for a clinician.
- Not generalisable beyond a 30-year-old, four-hospital, skewed-male benchmark.

### Q15.3 — What did you genuinely learn?
Integration cost is real and underestimated. Gluing tested components together surfaced interface bugs and behavioural mismatches that no unit test caught. Budget more time for integration than for any single component.

- **[Show]** [docs/Reflective_Synthesis_Paper.md §6](docs/Reflective_Synthesis_Paper.md).

### Q15.4 — Where does this pattern transfer?
Same shape (small classical model + RAG + structurally-guarded LLM + evaluator-critic) is being adopted in **legal**, **financial advisory**, and **insurance** for the same regulatory reasons. The transferable lesson: *the architecture is the safety story, not the prompt*.

---

## 16. Cross-examination drills

These are the gotcha questions a sceptical reviewer is most likely to throw.

### Q16.1 — "Did you actually write this, or did an AI write it?"
I designed the architecture, picked the thresholds, wrote the rubric, structured the tests, and made every responsible-AI tradeoff explicit. Where an LLM helped with boilerplate, the design decisions and their justifications are mine and are documented in [docs/Reflective_Synthesis_Paper.md](docs/Reflective_Synthesis_Paper.md). Every claim in the paper points back to a file in this repo — I can open any of them on demand.

### Q16.2 — "Explain RAG to me as if I've never heard of it."
A normal LLM answers from what it learned during training. A RAG-LLM is given a small set of documents at query time and **told to use only those**. That solves three problems: (a) the LLM can't hallucinate facts it wasn't given, (b) you can update the knowledge by editing a file, (c) every claim cites a source — you can audit it.

### Q16.3 — "What stops the LLM from inventing a citation like `[S99]`?"
Two things: the evaluator's rubric explicitly checks citation validity, **and** [src/evaluation.py](src/evaluation.py) `rag_faithfulness()` programmatically verifies every `[S#]` index is in range of the retrieved chunks. The Phase J audit in [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) cell 16 found **zero** invalid citations across three live runs.

### Q16.4 — "Show me the line that does the refusal."
[src/safeguards.py](src/safeguards.py) — `REFUSAL_SUBSTRINGS` tuple around line 14, `is_refused()` function around line 57. Called from [src/agent_orchestrator.py](src/agent_orchestrator.py) `run()` around line 156 **before** any model call.

### Q16.5 — "What's a sklearn `Pipeline` and why use one?"
A `Pipeline` is an ordered sequence of `(name, estimator)` steps where each step's output feeds the next, and the whole thing is treated as one object you can fit/predict/persist. Using it means preprocessing and the model are saved together — load `ml_model.joblib`, call `.predict_proba()`, and the same scaling/encoding that happened at training happens at inference. No room for "I forgot to scale at inference time" bugs.

### Q16.6 — "What's a `ColumnTransformer`?"
A `Pipeline` step that applies different transformations to different subsets of columns and stitches them back together. Here: numeric branch (impute median + log1p + standardise) on `NUMERIC_FEATURES`, categorical branch (impute most-frequent + one-hot) on `CATEGORICAL_FEATURES`. See [src/preprocessing.py](src/preprocessing.py) `build_preprocessor()` ~L39.

### Q16.7 — "Why two AUC numbers in the paper — CV and test?"
CV-AUC (~0.85) is the cross-validated estimate on the training data — a more conservative, less-biased estimate of generalisation. Test-AUC (~0.96) is on the held-out 61-row test set. The gap between them is large and is honest evidence that the test set is small/easy; both are reported, and bootstrap CIs are computed for the test number.

### Q16.8 — "Open the run log and show me one real run."
- **[Show output]** Open [outputs/run_log.jsonl](outputs/run_log.jsonl). Each line is one JSON object (JSONL — JSON Lines format) with `timestamp`, `run_id`, `event`, `payload`. Filter by any `run_id` (8 hex chars) — you'll see request → score → rag_search → draft → evaluation → (optional revision) → final_text. Refusal runs end after `refusal`.

### Q16.9 — "Why is `data/processed/` empty?"
Forward-compatible scaffolding. The pipeline does all preprocessing in-memory (the fitted preprocessor is pickled inside the model), so there's nothing to write to disk. Kept with a `.gitkeep` so the standard `raw → processed → models` folder shape survives a fresh clone.

### Q16.10 — "Why is the inner folder called `Intgerated AI Systems` with a typo?"
The original repository folder was named that way at commit time and renaming would break git history and external links. I left it and refer to it consistently throughout the docs. Everything inside is correctly named.

### Q16.11 — "Where does the `agreement_rate` number come from in nb05?"
[notebooks/05_integrated_pipeline.ipynb](notebooks/05_integrated_pipeline.ipynb) cell 8 computes `(abs(ml_prob - dl_prob) <= 0.20).mean()` across the entire scored test cohort. Same 0.20 threshold as the per-row confidence rule in [src/decision.py](src/decision.py).

### Q16.12 — "Why one evaluator pass + one revision, not five?"
Latency and cost cap. Each loop adds an LLM call (~1–3 seconds). Empirically one critique catches the structural issues (missing disclaimer, missing citation, missing uncertainty wording); deeper issues are content problems that more LLM passes don't fix. Tradeoff documented.

### Q16.13 — "What's the difference between `[S#]` and `cited_sources`?"
`[S#]` is the citation token the LLM puts in the text (e.g. `[S2]`). `cited_sources` (in the `Explanation` dataclass at [src/genai_explainer.py](src/genai_explainer.py) ~L64) is the resolved filename + heading that `[S#]` index points to — built by mapping the index back through the retrieved-chunk list.

### Q16.14 — "Show me a test that would fail if refusal logic broke."
[tests/test_agent_orchestrator.py](tests/test_agent_orchestrator.py) — the `test_refusal_path()` function asserts `result.refused is True` and that the event list contains no `llm_call` event. Run with `pytest tests/test_agent_orchestrator.py::test_refusal_path -v`.

### Q16.15 — "How would you extend this to a second disease?"
- Swap the dataset in [src/data_loader.py](src/data_loader.py) and update the feature lists in [src/preprocessing.py](src/preprocessing.py).
- Retrain (`python run_all.py` once, no flags).
- Replace the markdown files in [knowledge_base/](knowledge_base/) with the new condition's guidelines.
- Update the refusal substrings if the condition has new high-risk asks.
- Everything else — the agent loop, the evaluator, the audit log, the rubric — is condition-agnostic.

---

## 17. Worked example — one real row through every step

This section takes **one real patient row** (the first row of the deterministic test set, `seed=42`) and shows the **exact values** before and after each function. Every number below was captured live from the project's venv against the persisted models — paste any of it into a Python session and you'll get the same numbers back.

> **Reproduce these numbers**: open a venv shell from `Intgerated AI Systems/` and run the script at the end of this section, or just open [notebooks/05_integrated_pipeline.ipynb](notebooks/05_integrated_pipeline.ipynb) (cells 6–8 do almost exactly this on the cohort).

### 17.0 — The patient (raw row, before anything)

**Row identifier (traceable to source)**:
- pandas index: `219` — `df.iloc[219]`
- CSV row: line **221** of [data/raw/heart_disease.csv](data/raw/heart_disease.csv) (header is line 1, so data-row 220 → file-line 221)
- Recovery in code: `sp.X_test.iloc[[0]]` after `split_and_preprocess(df)` with `seed=42`
- Raw CSV line: `59,1,4,138,271,0,2,182,0,0.0,1,0.0,3.0,0,0`

**Row-view** (all 14 columns):

| | age | sex | cp | trestbps | chol | fbs | restecg | thalach | exang | oldpeak | slope | ca | thal | y_true |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `df.iloc[219]` | 59 | 1 | 4 | 138 | 271 | 0 | 2 | 182 | 0 | 0.0 | 1 | 0.0 | 3.0 | **0** |

**Column-view** (per-feature meaning):

| Column | Raw value | Type | Plain meaning |
|---|---|---|---|
| `age` | 59 | numeric | Age in years |
| `trestbps` | 138 | numeric | Resting systolic blood pressure (mmHg) |
| `chol` | 271 | numeric | Serum cholesterol (mg/dL) |
| `thalach` | 182 | numeric | Max heart rate achieved during exercise |
| `oldpeak` | 0.0 | numeric | ST-segment depression on ECG |
| `sex` | 1 | categorical | 1 = male |
| `cp` | 4 | categorical | Chest-pain type 4 (asymptomatic) |
| `fbs` | 0 | categorical | Fasting blood sugar ≤ 120 mg/dL |
| `restecg` | 2 | categorical | Resting ECG result code 2 |
| `exang` | 0 | categorical | No exercise-induced chest pain |
| `slope` | 1 | categorical | ST-slope code 1 |
| `ca` | 0.0 | categorical | 0 major vessels coloured by fluoroscopy |
| `thal` | 3.0 | categorical | Thalassemia code 3 (normal) |
| **`y_true`** | **0** | target | Held-out ground truth: no disease |

### 17.1 — Step 1: `data_loader.load_heart_disease()`

**Before** — nothing (just a URL).
**After** — a `pandas.DataFrame` of shape `(303, 15)` cached to [data/raw/heart_disease.csv](data/raw/heart_disease.csv).

```text
df.shape       == (303, 15)
df['num'].max() == 4   # original target: 0/1/2/3/4
df['target']    binarised: (num > 0).astype(int)  →  0 or 1
```

### 17.2 — Step 2: `split_and_preprocess()` — train/test split

**Before** — 303-row DataFrame.
**After** — deterministic stratified split (`test_size=0.2`, `random_state=42`):

```text
X_train.shape == (242, 13)
X_test.shape  == (61, 13)
```

The row we trace is `X_test.iloc[[0]]` — same row every run because of the seed.

### 17.3 — Step 3a: Numeric branch — `SimpleImputer(strategy="median")`

**What it does**: replaces missing values with the **training-set median** of each column. (Fitted on train, applied to test.)

**Effect on this row** — there are no missing numeric values, so the row is unchanged:

| Feature | Before | After impute |
|---|---|---|
| `age` | 59.0 | 59.0 |
| `trestbps` | 138.0 | 138.0 |
| `chol` | 271.0 | 271.0 |
| `thalach` | 182.0 | 182.0 |
| `oldpeak` | 0.0 | 0.0 |

(In other test rows where `ca` or `thal` was NaN, you'd see the train median substituted in. This row happens to be complete.)

### 17.4 — Step 3b: Numeric branch — `FunctionTransformer(np.log1p)`

**What it does**: applies `ln(1 + x)` element-wise. Compresses right-skew, safe at `x = 0`.

| Feature | Before | After log1p | Calculation |
|---|---|---|---|
| `age` | 59.0 | 4.0943 | `ln(60)` |
| `trestbps` | 138.0 | 4.9345 | `ln(139)` |
| `chol` | 271.0 | 5.6058 | `ln(272)` |
| `thalach` | 182.0 | 5.2095 | `ln(183)` |
| `oldpeak` | 0.0 | 0.0000 | `ln(1)` |

Note that `oldpeak = 0` becomes `0` exactly — this is the `+1` in `log1p` saving us from `ln(0) = -∞`.

### 17.5 — Step 3c: Numeric branch — `StandardScaler`

**What it does**: subtracts the train-set mean and divides by the train-set standard deviation. After this, each column has mean 0 and std 1 on the training set.

The fitted scaler (from training) holds:

```text
mean_   = [4.0035, 4.8739, 5.504,  5.0046, 0.558 ]   # mean of log1p(train) per column
scale_  = [0.1687, 0.1301, 0.2029, 0.1618, 0.5064]   # std of log1p(train) per column
```

Apply `(log1p_value - mean) / scale`:

| Feature | After log1p | Subtract mean | Divide by scale | **After scale** |
|---|---|---|---|---|
| `age` | 4.0943 | 4.0943 − 4.0035 = 0.0908 | / 0.1687 | **0.5386** |
| `trestbps` | 4.9345 | 0.0606 | / 0.1301 | **0.4656** |
| `chol` | 5.6058 | 0.1018 | / 0.2029 | **0.5017** |
| `thalach` | 5.2095 | 0.2049 | / 0.1618 | **1.2658** |
| `oldpeak` | 0.0000 | −0.558 | / 0.5064 | **−1.1020** |

Read the last column as "how many train-set standard deviations above (or below) the mean". `thalach` is +1.27 σ — this patient's exercise heart-rate is noticeably above the training-set average; `oldpeak` is −1.10 σ — well below average.

### 17.6 — Step 4a: Categorical branch — `SimpleImputer(strategy="most_frequent")`

**What it does**: fills missing categorical values with the most-common category in the training set. This row is complete, so nothing changes.

### 17.6 — Step 4b: Categorical branch — `OneHotEncoder(sparse_output=False)`

**What it does**: turns each categorical column with K levels into K binary columns (one `1` per row).

**Before** — 8 categorical values:
```text
{sex: 1, cp: 4, fbs: 0, restecg: 2, exang: 0, slope: 1, ca: 0, thal: 3}
```

**After** — 23 binary columns:

| Group | Output columns (order) | Row values |
|---|---|---|
| `sex` (2) | `sex_0, sex_1` | `0, 1` |
| `cp` (4) | `cp_1, cp_2, cp_3, cp_4` | `0, 0, 0, 1` |
| `fbs` (2) | `fbs_0, fbs_1` | `1, 0` |
| `restecg` (3) | `restecg_0, restecg_1, restecg_2` | `0, 0, 1` |
| `exang` (2) | `exang_0, exang_1` | `1, 0` |
| `slope` (3) | `slope_1, slope_2, slope_3` | `1, 0, 0` |
| `ca` (4) | `ca_0, ca_1, ca_2, ca_3` | `1, 0, 0, 0` |
| `thal` (3) | `thal_3, thal_6, thal_7` | `1, 0, 0` |

Total: 23 ones-and-zeros. Concatenated row:

```text
sex:    0, 1
cp:     0, 0, 0, 1
fbs:    1, 0
restecg:0, 0, 1
exang:  1, 0
slope:  1, 0, 0
ca:     1, 0, 0, 0
thal:   1, 0, 0
```

### 17.7 — Step 5: `ColumnTransformer` stitches branches together

5 numeric columns + 23 categorical columns = **28-column dense float matrix**, shape `(1, 28)`:

```text
[0.5386, 0.4656, 0.5017, 1.2658, -1.102,    # numeric (scaled log1p)
 0, 1,                                       # sex
 0, 0, 0, 1,                                 # cp
 1, 0,                                       # fbs
 0, 0, 1,                                    # restecg
 1, 0,                                       # exang
 1, 0, 0,                                    # slope
 1, 0, 0, 0,                                 # ca
 1, 0, 0]                                    # thal
```

This is the actual input to both the ML and DL models.

### 17.8 — Step 6: ML model — `HistGradientBoostingClassifier.predict_proba()`

**What it does**: walks the 300 trained boosted trees, sums their leaf contributions, applies sigmoid, returns the probability of class 1 (disease).

**Input**: the 28-column row above (sklearn `Pipeline` re-applies the same preprocessor on the raw row — same numbers).
**Output**:

```text
ml_prob = 0.5648
```

### 17.9 — Step 7: DL model — `MLPClassifier(...)` forward pass

**What it does**: pushes the same 28-column vector through `Linear(28→64) → ReLU → Dropout(0.3) → Linear(64→64) → ReLU → Dropout(0.3) → Linear(64→1)`, then sigmoid.

Note: at **inference** time, `Dropout` is a no-op (the model is in `.eval()` mode), so the output is deterministic.

**Output**:

```text
dl_prob = 0.5558
```

### 17.10 — Step 8: Decision layer — `score_patient()`

**Inputs**: `ml_prob = 0.5648`, `dl_prob = 0.5558`.

**Ensemble**:
```text
ensemble_prob = 0.5 * 0.5648 + 0.5 * 0.5558
              = 0.5603
```

**Tier** (`_tier` in [src/decision.py](src/decision.py) ~L46):
```text
low if ensemble_prob < 0.30
high if ensemble_prob >= 0.70
moderate otherwise
→ 0.5603 → "moderate"
```

**Confidence**:
```text
abs(ml_prob - dl_prob) = abs(0.5648 - 0.5558) = 0.009
0.009 <= 0.20  →  confidence = "high"
```

**Final `PatientScore`** (the structure passed to the explainer):
```text
ml_prob       = 0.5648
dl_prob       = 0.5558
ensemble_prob = 0.5603
tier          = "moderate"
confidence    = "high"
low_threshold = 0.3
high_threshold= 0.7
```

Held-out ground truth on this patient: `y_true = 0`. The model lands in the "moderate" band — exactly the case the wide moderate band is designed for: route to clinician review rather than commit.

### 17.11 — Step 9: Safeguard refusal check

For the demo3 row (request `"Prescribe a medication and dosage for this patient."`), [src/safeguards.py](src/safeguards.py) `is_refused()` runs the substring scan **before any LLM call**:

```text
REFUSAL_SUBSTRINGS contains "prescribe"
"Prescribe a medication and dosage for this patient.".lower().contains("prescribe") → True
→ short-circuit with RunResult(refused=True, refusal_reason="matched refusal substring: prescribe")
```

Real evidence — [docs/transcripts/demo3_refusal_0e9613d5.md](docs/transcripts/demo3_refusal_0e9613d5.md):

```text
- refused: True
- refusal_reason: matched refusal substring: prescribe
- revised: False

Event log: [request, refusal]   ← no llm_call, no draft, no evaluation
```

### 17.12 — Step 10: RAG retrieval (for the non-refused demo1 row)

Taking the actual demo1 row that ran on 2026-05-16, the orchestrator built this natural-language query from the patient's salient features:

```text
"Cardiovascular risk explanation for cp=4.0, thal=7.0, exang=1.0,
 oldpeak=0.0, slope=1.0, ca=0.0"
```

It embeds that query and retrieves `k=4` chunks from ChromaDB. Output (verbatim from [docs/transcripts/demo1_happy_path_608da255.md](docs/transcripts/demo1_happy_path_608da255.md)):

```json
{
  "query": "Cardiovascular risk explanation for cp=4.0, thal=7.0, exang=1.0, oldpeak=0.0, slope=1.0, ca=0.0",
  "n_results": 4,
  "sources": ["risk_factors.md", "feature_dictionary.md",
              "risk_factors.md", "feature_dictionary.md"]
}
```

### 17.13 — Step 11: Explainer LLM draft

`gpt-4o-mini` receives the system prompt + patient block + evidence block (4 chunks, labelled `[S1]`–`[S4]`) and produces (verbatim from the same transcript):

```text
High risk tier with an ensemble probability of 0.800 (low<0.3, high>=0.7).
Model agreement is low confidence; human review is recommended.

- Elevated cholesterol level (`chol` = 282.0) ... [S3]
- Exercise-induced angina (`exang` = 1) ... [S1]
- The presence of reversible perfusion defect (`thal` = 7) ... [S2]
- Resting blood pressure (`trestbps` = 126.0) ... [S4]
- The peak exercise capacity (`thalach` = 156.0) is above the
  age-predicted maximum, which is generally favorable ... [S3]   ← issue
...
```

### 17.14 — Step 12: Evaluator LLM verdict

`gpt-4o` scores the draft against the rubric. Verbatim output:

```json
{
  "pass": false,
  "score": 7,
  "issues": [
    "Unsupported claim about peak exercise capacity",
    "Incorrect interpretation of peak exercise capacity",
    "Missing citation for peak exercise capacity claim"
  ],
  "instructions": "Revise the explanation to remove the unsupported claim..."
}
```

### 17.15 — Step 13: Bounded revision (`max_revisions = 1`)

Because `pass = false` and `revisions < 1`, the explainer is called **once more** with the critic's instructions appended. The revised final text (verbatim):

```text
- The peak exercise capacity (`thalach` = 156.0) is not explicitly
  linked to risk in the provided evidence, thus its interpretation
  should be approached with caution.
```

The bad claim is gone. Transcript front-matter now says `revised: True`. Audit trail is the full event chain in [outputs/run_log.jsonl](outputs/run_log.jsonl).

### 17.16 — Recap: one row, every transformation, in one table

| # | Step | Function | Shape in | Shape out | Sample value (from this row) |
|---|---|---|---|---|---|
| 1 | Load CSV | `load_heart_disease()` | — | `(303, 15)` | `age=59, chol=271, …` |
| 2 | Split | `split_and_preprocess()` | `(303, 13)` | `(242,13)+(61,13)` | row = `X_test.iloc[[0]]` |
| 3a | Impute numeric | `SimpleImputer(median)` | `(1, 5)` | `(1, 5)` | unchanged (no NaNs) |
| 3b | Log-scale skew | `np.log1p` | `(1, 5)` | `(1, 5)` | `chol: 271 → 5.6058` |
| 3c | Standardise | `StandardScaler` | `(1, 5)` | `(1, 5)` | `chol: 5.6058 → 0.5017` |
| 4 | One-hot cat | `OneHotEncoder` | `(1, 8)` | `(1, 23)` | `cp=4 → [0,0,0,1]` |
| 5 | Stitch | `ColumnTransformer` | — | `(1, 28)` | dense float vector |
| 6 | ML score | `HGB.predict_proba` | `(1, 28)` | scalar | `0.5648` |
| 7 | DL score | `MLP forward + sigmoid` | `(1, 28)` | scalar | `0.5558` |
| 8 | Ensemble | `0.5*ml + 0.5*dl` | 2 scalars | scalar | `0.5603` |
| 9 | Tier | `_tier(ensemble)` | scalar | label | `"moderate"` |
| 10 | Confidence | `abs(ml-dl) <= 0.20` | 2 scalars | label | `"high"` |
| 11 | Refusal | `is_refused(request)` | string | bool | `False` here, `True` for demo3 |
| 12 | RAG retrieval | `vector_store.query(k=4)` | query | 4 chunks | `risk_factors.md, …` |
| 13 | Explainer | `gpt-4o-mini` | prompt | draft text + `[S#]` | 5-bullet explanation |
| 14 | Evaluator | `gpt-4o` | draft | JSON verdict | `pass: false, score: 7` |
| 15 | Revision (≤1) | `_revise()` | issues | fixed text | bad claim removed |
| 16 | Persist | `save_transcript()` + `_log()` | result | `.md` + JSONL | `docs/transcripts/demo1_*` + `outputs/run_log.jsonl` |

### 17.17 — Reproduce this entire table yourself

Open a venv shell from `Intgerated AI Systems/` and run:

```python
import sys, numpy as np
sys.path.insert(0, ".")
from src.data_loader import load_heart_disease, NUMERIC_FEATURES, CATEGORICAL_FEATURES
from src.preprocessing import split_and_preprocess
from src.decision import load_default_scorers, score_patient

df = load_heart_disease()
sp = split_and_preprocess(df)
row = sp.X_test.iloc[[0]]

num_branch = sp.preprocessor.named_transformers_["num"]
num = row[NUMERIC_FEATURES].values
print("raw         :", num.tolist()[0])
print("after impute:", num_branch.named_steps["impute"].transform(num).round(4).tolist()[0])
print("after log1p :", num_branch.named_steps["log1p"].transform(
        num_branch.named_steps["impute"].transform(num)).round(4).tolist()[0])
print("after scale :", num_branch.transform(num).round(4).tolist()[0])

ml, dl, pp = load_default_scorers(sp)
ps = score_patient(row, ml, dl, pp)
print("PatientScore:", ps)
```

You should see the same numbers printed in this section.

---



| Short | Full form / definition |
|---|---|
| Adam | Adaptive Moment Estimation — an adaptive-learning-rate optimizer for neural networks |
| AI | Artificial Intelligence |
| ANN | Approximate Nearest-Neighbour (search) |
| API | Application Programming Interface |
| AUC | Area Under the Curve |
| BCE / BCEWithLogitsLoss | Binary Cross-Entropy / numerically-stable variant that combines sigmoid + BCE |
| Brier score | Mean squared error of probability forecasts (lower is better) |
| CAD | Coronary Artery Disease |
| ChromaDB | Chroma vector Database |
| CI | Confidence Interval |
| ColumnTransformer | sklearn class that applies different transforms to different column subsets |
| Cramer's V | Chi-square-based association statistic for two categorical variables |
| CSV | Comma-Separated Values |
| CV | Cross-Validation |
| DL | Deep Learning |
| Dropout | Training-time regularization that zeros out a fraction of activations |
| ECG | Electrocardiogram — recording of the heart's electrical activity |
| EHR | Electronic Health Record |
| Ensemble | Combining outputs of multiple models (here: simple average) |
| EU AI Act | European Union Artificial Intelligence Act |
| FDA | (US) Food and Drug Administration |
| GDPR | General Data Protection Regulation (EU) |
| GenAI | Generative Artificial Intelligence |
| Gradient boosting | Sequential tree-building where each tree corrects the previous one's errors |
| GUID / UUID | Globally / Universally Unique Identifier |
| HGB | HistGradientBoostingClassifier — sklearn histogram-based gradient boosting |
| HIPAA | Health Insurance Portability and Accountability Act (US) |
| HNSW | Hierarchical Navigable Small World (vector-index graph algorithm) |
| ID | Identifier |
| IDA | Initial Data Analysis |
| Imputer | Fills in missing values (here: median for numeric, most-frequent for categorical) |
| IRB | Institutional Review Board |
| JSON | JavaScript Object Notation |
| JSONL | JSON Lines — one JSON object per line |
| joblib | Python serialization library optimized for large NumPy arrays |
| L2 regularization | Penalises sum of squared weights to discourage large weights |
| LangChain | A popular Python framework for chaining LLM calls (not a dependency here; referenced as a pattern) |
| LightGBM | Light Gradient-Boosting Machine — Microsoft's gradient-boosting library |
| `log1p` | `ln(1 + x)` — natural log of `1 + x`, safe at `x = 0`, compresses right-skew |
| LLM | Large Language Model |
| Loss function | Number that quantifies how wrong a model's predictions are; training minimises it |
| ML | Machine Learning |
| MLP | Multi-Layer Perceptron — feed-forward neural network |
| nb04 / nb05 | Shorthand for [notebooks/04_evaluation.ipynb](notebooks/04_evaluation.ipynb) and [notebooks/05_integrated_pipeline.ipynb](notebooks/05_integrated_pipeline.ipynb) |
| NIST AI RMF | National Institute of Standards and Technology — Artificial Intelligence Risk Management Framework |
| NumPy | Numerical Python — the array-computing library |
| Optimizer | Algorithm that updates model weights to reduce loss (e.g. SGD, Adam) |
| OneHotEncoder | Turns one categorical column with K values into K binary columns |
| OpenAI | The vendor of `gpt-4o`, `gpt-4o-mini`, and `text-embedding-3-small` used here |
| P2…P6 | Udacity nanodegree capstone Projects 2 through 6 |
| PHI | Protected Health Information |
| Pipeline (sklearn) | Ordered sequence of (name, estimator) steps treated as one object |
| PR-AUC | Precision-Recall — Area Under the Curve |
| `pytest` | The Python testing framework |
| PyTorch | Facebook/Meta's deep-learning library |
| RAG | Retrieval-Augmented Generation |
| ReLU | Rectified Linear Unit — `max(0, x)` activation function |
| Regularization | Techniques that prevent overfitting (Dropout, L2, early stopping, etc.) |
| ROC | Receiver Operating Characteristic |
| ROC-AUC | Receiver Operating Characteristic — Area Under the Curve |
| RNG | Random-Number Generator |
| SaMD | Software as a Medical Device |
| Seed | A fixed integer that makes pseudo-random operations deterministic |
| SHA-256 | Secure Hash Algorithm, 256-bit |
| sklearn / scikit-learn | The standard Python machine-learning library |
| SQL | Structured Query Language |
| SQLite | SQL, lite/embedded variant — a single-file relational database |
| `state_dict` | PyTorch's serializable Python dict of layer weights |
| StandardScaler | Subtracts mean, divides by standard deviation per column |
| ST depression | A specific dip in the ECG's ST segment, associated with ischemia (insufficient blood supply) |
| StratifiedKFold | K-fold CV that preserves class balance across folds |
| std | Standard deviation |
| thalassemia | A blood disorder; encoded as a stress-test result column here |
| UCI | University of California, Irvine — the Machine Learning Repository hosted there |
| UI | User Interface |
| UTC | Coordinated Universal Time |
| WHO | World Health Organization |
| XGBoost | eXtreme Gradient Boosting — a popular gradient-boosting library |

---

**End of Defense FAQ v2.** Every section anchors to a file or notebook cell you can open in VS Code on demand.
