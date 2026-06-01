"""Render docs/dl_mlp_architecture.png as a perceptron-style MLP diagram.

This uses local matplotlib rendering (no external web service).
Run from project root:
    python scripts/render_mlp_architecture_local.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "dl_mlp_architecture.png"


def _draw_neuron(ax, x: float, y: float, text: str, fc: str = "#e3f2fd") -> None:
    circ = plt.Circle((x, y), 0.18, facecolor=fc, edgecolor="#1976d2", linewidth=1.5)
    ax.add_patch(circ)
    ax.text(x, y, text, ha="center", va="center", fontsize=9)


def _draw_edges(ax, xs: list[tuple[float, float]], ys: list[tuple[float, float]], alpha: float = 0.35) -> None:
    for x0, y0 in xs:
        for x1, y1 in ys:
            ax.plot([x0, x1], [y0, y1], color="#455a64", alpha=alpha, linewidth=1.0)


def render() -> None:
    fig, ax = plt.subplots(figsize=(12, 7), dpi=180)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")

    input_nodes = [(1.5, 6.5), (1.5, 5.5), (1.5, 4.5), (1.5, 3.5)]
    h1_nodes = [(4.5, 6.5), (4.5, 5.3), (4.5, 4.1), (4.5, 2.9)]
    h2_nodes = [(7.5, 6.5), (7.5, 5.3), (7.5, 4.1), (7.5, 2.9)]
    out_node = (10.5, 4.9)
    prob_node = (10.5, 3.2)

    for (x, y), label in zip(input_nodes, ["x1", "x2", "x3", "... xn"]):
        _draw_neuron(ax, x, y, label, fc="#f1f8e9")

    for (x, y), label in zip(h1_nodes, ["h1_1", "h1_2", "...", "h1_64"]):
        _draw_neuron(ax, x, y, label)

    for (x, y), label in zip(h2_nodes, ["h2_1", "h2_2", "...", "h2_64"]):
        _draw_neuron(ax, x, y, label)

    _draw_neuron(ax, out_node[0], out_node[1], "z", fc="#fff3e0")
    _draw_neuron(ax, prob_node[0], prob_node[1], "p", fc="#fff3e0")

    _draw_edges(ax, input_nodes, h1_nodes, alpha=0.3)
    _draw_edges(ax, h1_nodes, h2_nodes, alpha=0.3)
    _draw_edges(ax, h2_nodes, [out_node], alpha=0.4)
    ax.plot([out_node[0], prob_node[0]], [out_node[1] - 0.2, prob_node[1] + 0.2], color="#455a64", linewidth=1.2)

    ax.text(1.5, 7.35, "Input layer", ha="center", fontsize=11, fontweight="bold")
    ax.text(4.5, 7.35, "Hidden layer 1 (64 perceptrons)", ha="center", fontsize=11, fontweight="bold")
    ax.text(7.5, 7.35, "Hidden layer 2 (64 perceptrons)", ha="center", fontsize=11, fontweight="bold")
    ax.text(10.5, 7.35, "Output", ha="center", fontsize=11, fontweight="bold")

    ax.text(4.5, 2.1, "ReLU + Dropout(0.3)", ha="center", fontsize=10, color="#ef6c00")
    ax.text(7.5, 2.1, "ReLU + Dropout(0.3)", ha="center", fontsize=10, color="#ef6c00")
    ax.text(10.5, 2.4, "p = sigmoid(z)", ha="center", fontsize=10, color="#ef6c00")

    ax.text(6.0, 1.2, "Each perceptron computes: a = activation(w dot x + b)", ha="center", fontsize=10)
    ax.text(6.0, 0.7, "Training: BCEWithLogitsLoss, Adam(lr=1e-3, wd=1e-4), batch=32, epochs=80", ha="center", fontsize=9)

    fig.suptitle("DL Tabular MLP (Neuron/Perceptron View)", fontsize=14, fontweight="bold", y=0.98)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    render()
