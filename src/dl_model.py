"""Deep-learning risk model for the Heart Disease cohort.

A small PyTorch MLP that consumes the same preprocessed tabular features
as the gradient-boosting baseline and predicts the binary disease label.

Lineage: the training-loop discipline (fixed seed, deterministic init,
dropout regularization, per-epoch loss/accuracy logging, per-slice
disaggregated evaluation, CPU-budget honesty) is adapted from Project 4
(Deep Learning, Fashion-MNIST CNN with dropout). The implementation here
is a fresh tabular MLP, not a CNN.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from .config import settings
from .preprocessing import RANDOM_STATE, SplitData

MODEL_PATH = settings.models_dir / "dl_model.pt"
META_PATH = settings.models_dir / "dl_model_meta.pt"


def set_seed(seed: int = RANDOM_STATE) -> None:
    # Seed every RNG the training loop touches: Python `random` for shuffles,
    # NumPy for tensor init helpers, and PyTorch for layer init + dropout.
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class MLPClassifier(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, dropout: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


@dataclass
class DLMetrics:
    test_roc_auc: float
    test_pr_auc: float
    test_brier: float
    epochs: int
    history: list[dict] = field(default_factory=list)


def _to_tensor(arr: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(np.asarray(arr, dtype=np.float32))


def train_and_evaluate(
    split: SplitData,
    epochs: int = 80,
    batch_size: int = 32,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    hidden_dim: int = 64,
    dropout: float = 0.3,
    seed: int = RANDOM_STATE,
) -> tuple[MLPClassifier, DLMetrics]:
    set_seed(seed)

    X_train = split.preprocessor.transform(split.X_train)
    X_test = split.preprocessor.transform(split.X_test)
    y_train = split.y_train.values.astype(np.float32)
    y_test = split.y_test.values.astype(np.float32)

    train_ds = TensorDataset(_to_tensor(X_train), _to_tensor(y_train))
    test_ds = TensorDataset(_to_tensor(X_test), _to_tensor(y_test))
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    model = MLPClassifier(input_dim=X_train.shape[1], hidden_dim=hidden_dim, dropout=dropout)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    criterion = nn.BCEWithLogitsLoss()

    history: list[dict] = []
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * xb.size(0)
        train_loss /= len(train_ds)

        model.eval()
        with torch.no_grad():
            test_loss = 0.0
            probs_list, y_list = [], []
            for xb, yb in test_loader:
                logits = model(xb)
                loss = criterion(logits, yb)
                test_loss += loss.item() * xb.size(0)
                probs_list.append(torch.sigmoid(logits).numpy())
                y_list.append(yb.numpy())
            test_loss /= len(test_ds)
            probs_epoch = np.concatenate(probs_list)
            y_epoch = np.concatenate(y_list)
            auc = float(roc_auc_score(y_epoch, probs_epoch)) if len(np.unique(y_epoch)) > 1 else float("nan")
        history.append(
            {"epoch": epoch, "train_loss": train_loss, "test_loss": test_loss, "test_auc": auc}
        )

    model.eval()
    with torch.no_grad():
        probs = torch.sigmoid(model(_to_tensor(X_test))).numpy()

    metrics = DLMetrics(
        test_roc_auc=float(roc_auc_score(y_test, probs)),
        test_pr_auc=float(average_precision_score(y_test, probs)),
        test_brier=float(brier_score_loss(y_test, probs)),
        epochs=epochs,
        history=history,
    )
    return model, metrics


def save(model: MLPClassifier, input_dim: int, path: Path = MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), path)
    torch.save({"input_dim": input_dim}, META_PATH)
    return path


def load(path: Path = MODEL_PATH) -> MLPClassifier:
    meta = torch.load(META_PATH, weights_only=True)
    model = MLPClassifier(input_dim=meta["input_dim"])
    model.load_state_dict(torch.load(path, weights_only=True))
    model.eval()
    return model


def predict_proba(model: MLPClassifier, preprocessor, X: pd.DataFrame) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        x = _to_tensor(preprocessor.transform(X))
        return torch.sigmoid(model(x)).numpy()


def slice_metrics(
    model: MLPClassifier,
    preprocessor,
    X: pd.DataFrame,
    y: pd.Series,
    slice_col: str,
) -> pd.DataFrame:
    """Per-slice ROC-AUC + positive rate.

    Lineage: P4 — disaggregated evaluation surfaced 'same headline accuracy,
    different per-class behaviour'. We apply the same discipline across
    clinical sub-cohorts (e.g. by sex or age band).
    """
    probs = predict_proba(model, preprocessor, X)
    rows = []
    for value, idx in X.groupby(slice_col).groups.items():
        idx = list(idx)
        y_slice = y.loc[idx]
        positions = X.index.get_indexer(idx)
        if y_slice.nunique() < 2 or len(y_slice) < 10:
            auc = float("nan")
        else:
            auc = float(roc_auc_score(y_slice, probs[positions]))
        rows.append(
            {
                slice_col: value,
                "n": len(idx),
                "positive_rate": float(y_slice.mean()),
                "roc_auc": auc,
            }
        )
    return pd.DataFrame(rows)
