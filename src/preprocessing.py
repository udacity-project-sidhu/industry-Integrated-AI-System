"""Preprocessing pipeline for the Heart Disease tabular task.

Lineage: the `log1p` + `StandardScaler` + scikit-learn `ColumnTransformer`
pattern is adapted from Project 3 (Machine Learning, UCI Online Retail II
K-Means RFM segmentation), reapplied here in a supervised setting with
one-hot encoding for categorical features.

It turns a raw UCI Heart Disease patient row (mixed numeric + categorical, 
possibly with missing cells) into a fully numeric, mean-0 / std-1 feature vector 
that the ML and DL models can both consume — using a single reusable 
scikit-learn ColumnTransformer so the exact same transformation runs at 
training time and at inference time.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from .data_loader import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    TARGET_COL,
    feature_columns,
)

RANDOM_STATE = 42


@dataclass
class SplitData:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    preprocessor: ColumnTransformer


def build_preprocessor() -> ColumnTransformer:
    log1p = FunctionTransformer(np.log1p, validate=False, feature_names_out="one-to-one")
    numeric_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("log1p", log1p),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, NUMERIC_FEATURES),
            ("cat", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )


def split_and_preprocess(
    df: pd.DataFrame, test_size: float = 0.2, random_state: int = RANDOM_STATE
) -> SplitData:
    X = df[feature_columns()].copy()
    y = df[TARGET_COL].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    preprocessor = build_preprocessor()
    preprocessor.fit(X_train)

    return SplitData(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        preprocessor=preprocessor,
    )

"""
The dataset has 13 features (5 numeric, 8 categorical) plus a binary target.

Numeric columns: age, trestbps (resting BP), chol (cholesterol), thalach (max heart rate), oldpeak (ST depression).
Categorical columns: sex, cp (chest-pain type), fbs, restecg, exang, slope, ca, thal.

BEFORE (one raw patient row)
age	trestbps	chol	thalach	oldpeak	sex	cp	fbs	restecg	exang	slope	ca	thal
63	145	        233	    150	    2.3	    1	3	1	0	    0	    0	    0	1
Problems with this row as-is:

chol = 233 and oldpeak = 2.3 are on completely different scales — gradient-based models (the PyTorch MLP) 
would let cholesterol dominate just because its numbers are bigger.
cp = 3 looks numeric but is a category label (chest-pain type 3 is not "three times" type 1). Feeding it as an 
integer tells the model a false ordering.
A real row may have NaN cells — neither model accepts NaN.

After the preprocessing pipeline, the same patient row becomes a 17-dimensional numeric vector:
[ +0.95  +0.76  -0.26  +0.02  +1.09     # 5 numeric: log1p → standardised

  0 1   0 0 0 1   0 1   1 0 0   1 0   1 0 0   1 0 0 0   0 1 0 0 ]
#  sex   cp        fbs    restecg  exang   slope     ca         thal

What changed:

The 5 numeric values are now small, comparable, signed numbers near 0.
The 8 categorical columns expanded into ~20 binary 0/1 columns (one per observed category).
Any NaN was filled (median for numerics, most-frequent for categoricals) before transforming.
The final vector is ~25 floats, fully numeric, with no column on a wildly different scale.

----------------------------------------------------------------------------------
1. log1p — compress long-tailed numbers
Definition: log1p(x) = ln(1 + x). The +1 makes it safe when x = 0.

Why use it: features like chol and oldpeak have a long right tail 
(a few patients with very high cholesterol). 
Linear models and neural nets see these as outliers and over-weight them. 
Taking the log pulls the tail in so the distribution looks more bell-shaped.

Example on chol values:

Raw chol	log1p(chol)
0	        0.000
200     	5.303
250	        5.525
300	        5.707
600	        6.398

Notice the raw range is 0 → 600 (×∞ ratio), 
but after log1p it's 0 → 6.4 — the difference between a "high" and a "very high" 
cholesterol patient is now a small step, not a giant one.

------------------------------------------------------------------------------------

2. StandardScaler — put every feature on the same ruler
Definition: for each column, compute its mean μ and standard deviation σ on the training data, 
then transform every value with
x' = (x - μ) / σ 

After this, the column has mean ≈ 0 and std ≈ 1.

Why it matters: the MLP in src/dl_model.py uses gradient descent. 
If chol is in the hundreds and oldpeak is < 5, gradients on chol swamp 
gradients on oldpeak — the network effectively ignores oldpeak until very late in training. 
Standardising puts every numeric feature on equal footing.

example. Suppose after log1p, training chol has mean = 5.5, std = 0.3.

Raw 	After 	After StandardScaler 
chol    log1p      ((x − 5.5)/0.3)
200	    5.303	−0.66
250	    5.525	+0.08
300	    5.707	+0.69
600	    6.398	+2.99 ← clearly flagged as far above average
Critical detail: StandardScaler is fit only on X_train (see preprocessor.fit(X_train) 
at line 73). Test rows are transformed with the training μ and 
σ — fitting on the test set would leak information.

------------------------------------------------------------------------------------
3. ColumnTransformer — apply different recipes to different columns
A Pipeline is a vertical chain (impute → log1p → scale). 
A ColumnTransformer is a horizontal split: route each set of columns to its own pipeline, 
then concatenate the outputs.

raw row (13 cols)
     │
     ├──► [age, trestbps, chol, thalach, oldpeak] ──► impute(median) → log1p → StandardScaler ──► 5 floats
     │
     └──► [sex, cp, fbs, restecg, exang, slope, ca, thal] ──► impute(most_frequent) → OneHotEncoder ──► ~20 binary floats
                                                                                                              │
                                       concatenated side-by-side ◄─────────────────────────────────────────────┘
                                                       │
                                                       ▼
                                       single numeric vector (~25 cols)
Why this matters:

One object, one fit. The whole recipe (medians, μ/σ, learned categories) is stored inside the ColumnTransformer. 
At inference time you just call preprocessor.transform(new_row) and get the identical encoding.
No data leakage between train and test. Both halves are fit on X_train only.
No bookkeeping bugs. You can't accidentally one-hot encode age or scale sex.

---------------------------------------------------------------------------------
4. OneHotEncoder — turn categorical columns into binary vectors
Definition: for each categorical column, find all the unique categories in the training set.

A categorical column like cp (chest-pain type) has values {0, 1, 2, 3} 
— they look numeric but they are names, not amounts. 
cp = 3 is not "three times more chest pain" than cp = 1.

One-hot encoding replaces one such column with one binary column per category. 
Exactly one of them is 1; the rest are 0.

Example on cp:

Raw-cp	cp_0	cp_1	cp_2	cp_3   CP-transformed
0	    1	    0	    0	    0      1,0,0,0
1	    0	    1	    0	    0      0,1,0,0
2	    0	    0	    1	    0      0,0,1,0
3	    0	    0	    0	    1      0,0,0,1
Why this is necessary:

It removes the false ordering the model would otherwise learn (it would assume cp=3 is "bigger" than cp=1).
It removes false distance assumptions (the model would treat cp=3 as further from cp=1 than cp=2).
Each category gets its own independent weight, which is what you want when categories represent kinds, not amounts.
For all 8 categorical columns combined, the output is ~20 binary columns (the exact count depends on how many unique 
categories appeared in X_train).

The config in preprocessing.py:
OneHotEncoder(handle_unknown="ignore", sparse_output=False)
handle_unknown="ignore" — if a test patient has a category never seen at training time (e.g. thal = 9), 
produce all zeros instead of crashing. Important for a deployed system.
sparse_output=False — return a regular dense NumPy array, easier to concatenate and inspect.

Downstream, src/ml_model.py (HGB) and src/dl_model.py (MLP) both call preprocessor.transform(X) 
on whatever row comes in — training row, test row, or a single live patient from the agent. 
The encoding is guaranteed identical across all three call sites, which is why the audit trail 
in outputs/run_log.jsonl is reproducible.

-----------------------------------------------------------------------------

Using one real-looking patient row through the pipeline in src/preprocessing.py. The μ and σ numbers below are realistic values learned from the UCI Heart Disease training split; the demo NaN is shown so you can see imputation happen.

Stage 0 — Raw row in (13 columns, one of them missing)
age	trestbps	chol	thalach	oldpeak	sex	cp	fbs	restecg	exang	slope	ca	thal
63	145	NaN	150	2.3	1	3	1	0	0	0	0	1
ColumnTransformer now splits this row into two streams.

Numeric stream — [age, trestbps, chol, thalach, oldpeak]

Step N1 — SimpleImputer(strategy="median")
Median values learned from training data: age=55, trestbps=130, chol=240, thalach=153, oldpeak=0.8. Only chol is missing, so only chol changes:

age	trestbps	chol	thalach	oldpeak
63	145	240 ← filled	150	2.3

Step N2 — log1p (x → ln(1+x))
age	trestbps	chol	thalach	oldpeak
ln(64) = 4.159	ln(146) = 4.984	ln(241) = 5.485	ln(151) = 5.017	ln(3.3) = 1.194

Step N3 — StandardScaler (z = (x − μ) / σ)
Training μ / σ of the log1p'd column (these are what StandardScaler.fit stored):

column	μ (post-log1p)	σ (post-log1p)
age	4.00	0.17
trestbps	4.88	0.13
chol	5.50	0.21
thalach	5.02	0.16
oldpeak	0.62	0.46
Applying the formula:

feature	calculation	z
age	(4.159 − 4.00) / 0.17	+0.94
trestbps	(4.984 − 4.88) / 0.13	+0.80
chol	(5.485 − 5.50) / 0.21	−0.07
thalach	(5.017 − 5.02) / 0.16	−0.02
oldpeak	(1.194 − 0.62) / 0.46	+1.25

Numeric stream output (5 floats):
[ +0.94,  +0.80,  -0.07,  -0.02,  +1.25 ]

Plain reading: this patient is older than average (+0.94σ), has higher BP than average (+0.80σ), 
roughly average cholesterol (−0.07σ), average max heart rate (−0.02σ), and 
clearly elevated ST depression (+1.25σ).

Categorical stream — [sex, cp, fbs, restecg, exang, slope, ca, thal]
Step C1 — SimpleImputer(strategy="most_frequent")
No missing values in this row, so this is a no-op:

sex	cp	fbs	restecg	exang	slope	ca	thal
1	3	1	0	0	0	0	1
Step C2 — OneHotEncoder
Each column expands into one binary indicator per category seen in training. The bold 1 marks the patient's value; everything else is 0.

original	categories learned	expansion for this row
sex = 1	{0, 1}	sex_0=0, sex_1=1
cp = 3	{0, 1, 2, 3}	cp_0=0, cp_1=0, cp_2=0, cp_3=1
fbs = 1	{0, 1}	fbs_0=0, fbs_1=1
restecg=0	{0, 1, 2}	restecg_0=1, restecg_1=0, restecg_2=0
exang = 0	{0, 1}	exang_0=1, exang_1=0
slope = 0	{0, 1, 2}	slope_0=1, slope_1=0, slope_2=0
ca = 0	{0, 1, 2, 3}	ca_0=1, ca_1=0, ca_2=0, ca_3=0
thal = 1	{0, 1, 2, 3}	thal_0=0, thal_1=1, thal_2=0, thal_3=0

Categorical stream output (22 binary floats):
sex   cp          fbs    restecg   exang      slope        ca               thal
[0,1, 0,0,0,1,    0,1,   1,0,0,      1,0,     1,0,0,       1,0,0,0,         0,1,0,0]

shape: (1, 27)

That single 27-element vector is what gets handed to:

HistGradientBoostingClassifier.predict_proba() in src/ml_model.py, and
the PyTorch MLP.forward() in src/dl_model.py,
and then the two model probabilities are averaged by src/decision.py to produce the triage tier the agent explains.

Side-by-side summary for this row
Before	After
Shape	1 row × 13 mixed cols (with NaN)	1 row × 27 floats (no NaN, all numeric)
Numeric values	raw, different scales (e.g. chol=240, oldpeak=2.3)	mean-0 / std-1 z-scores (e.g. −0.07, +1.25)
Categorical values	integer labels with false ordering (e.g. cp=3)	independent 0/1 indicator columns (cp_3=1, rest 0)
Missing cells	chol = NaN	filled with training median (240) before any math
Model-readable?	No (NaN + scale mismatch + fake ordering)	Yes — same encoding at train, test, and live-inference time
That equivalence between training-time and inference-time encoding is the whole reason the system can be audited: 
any row in outputs/run_log.jsonl can be replayed through the same fitted preprocessor and reproduce the 
exact 27-element vector the models saw.

"""