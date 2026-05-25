r"""Smoke test for the DL risk model.

cd 'C:\Users\dev\sources\udacity\Project 7 - Industry-integrated AI System\Intgerated AI Systems'

python -m pytest tests/test_dl_model.py

python -m pytest tests/test_dl_model.py -s

# or more verbose:
python -m pytest tests/test_dl_model.py -s -v

--------------------------------------------------------------------------------

A smoke test for the Deep Learning risk model (dl_model.py — a PyTorch neural net, the sibling of the scikit-learn classifier in ml_model.py).

One test: test_dl_model_trains_and_persists()
Three concerns, end-to-end:

Trains — runs train_and_evaluate(split, epochs=10) on the Heart Disease split. 
Only 10 epochs to keep the test fast (real training would use more).
Performs better than chance — asserts 0.5 < test_roc_auc <= 1.0. ROC-AUC = 0.5 is random guessing; 
anything above means the model has actually learned signal from the features. 
The upper bound just guards against impossible/buggy values.
Persists to disk — saves the model with save(model, input_dim=...) and asserts the file actually exists. 
The input_dim is required because, unlike the sklearn Pipeline (which carries preprocessing), 
the PyTorch net needs to know how many input features the first layer expects when it's reloaded.
What it does NOT test
A specific accuracy / AUC threshold (just "better than random").
Calibration (Brier score), PR-AUC, or per-slice fairness.
Reload-and-predict (it saves, but doesn't load back and run inference).
Reproducibility / seeding.
Integration with the ensemble or orchestrator (that's test_decision.py / test_agent_orchestrator.py).
Cost / time
Offline. Trains a fresh net every run — slower than the data-pipeline tests, faster than the full 
orchestrator test. No OpenAI key needed.

What this guards against
If someone breaks the model architecture, training loop, metric computation, or save format, 
this one assert fails fast — before the decision layer or agent orchestrator gets a chance to fail with a more confusing error downstream.

"""
from __future__ import annotations

from src.data_loader import load_heart_disease
from src.dl_model import save, train_and_evaluate
from src.preprocessing import split_and_preprocess


def test_dl_model_trains_and_persists():
    df = load_heart_disease()
    split = split_and_preprocess(df)
    model, metrics = train_and_evaluate(split, epochs=10)
    assert 0.5 < metrics.test_roc_auc <= 1.0
    input_dim = split.preprocessor.transform(split.X_train).shape[1]
    path = save(model, input_dim=input_dim)
    assert path.exists()
