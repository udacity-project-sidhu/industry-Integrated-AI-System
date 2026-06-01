"""Render a perceptron-style MLP architecture diagram directly to PNG.

This avoids Mermaid limitations by drawing neuron circles and weighted
connections with matplotlib.

Run from project root:
    python scripts/render_mlp_neuron_diagram.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle


def _layer_y_positions(n: int, y_min: float = 0.10, y_max: float = 0.90) -> list[float]:
    if n <= 1:
        return [0.5]
    step = (y_max - y_min) / (n - 1)
    return [y_min + i * step for i in range(n)]


def _draw_layer(ax, x: float, y_positions: list[float], radius: float, color: str) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    for y in y_positions:
        ax.add_patch(Circle((x, y), radius=radius, facecolor=color, edgecolor="#1a1a1a", linewidth=1.2))
        coords.append((x, y))
    return coords


def _connect(ax, left: list[tuple[float, float]], right: list[tuple[float, float]], alpha: float = 0.18) -> None:
    for x1, y1 in left:
        for x2, y2 in right:
            ax.plot([x1, x2], [y1, y2], color="#4f5d75", linewidth=0.8, alpha=alpha, zorder=0)


def render() -> Path:
    fig, ax = plt.subplots(figsize=(14, 8), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fcfcfc")

    # Layer layout
    x_input = 0.12
    x_h1 = 0.38
    x_h2 = 0.62
    x_out = 0.86
    radius = 0.018

    # Visualized neuron counts (representative); labels carry true dimensions.
    input_nodes = _draw_layer(ax, x_input, _layer_y_positions(8), radius, "#d9edf7")
    h1_nodes = _draw_layer(ax, x_h1, _layer_y_positions(10), radius, "#dff0d8")
    h2_nodes = _draw_layer(ax, x_h2, _layer_y_positions(10), radius, "#dff0d8")
    out_nodes = _draw_layer(ax, x_out, _layer_y_positions(1), radius, "#f2dede")

    _connect(ax, input_nodes, h1_nodes)
    _connect(ax, h1_nodes, h2_nodes)
    _connect(ax, h2_nodes, out_nodes, alpha=0.28)

    # Layer labels
    ax.text(x_input, 0.96, "Input layer", ha="center", va="bottom", fontsize=13, weight="bold")
    ax.text(x_input, 0.92, "input_dim features", ha="center", va="bottom", fontsize=11)

    ax.text(x_h1, 0.96, "Hidden layer 1", ha="center", va="bottom", fontsize=13, weight="bold")
    ax.text(x_h1, 0.92, "64 perceptrons", ha="center", va="bottom", fontsize=11)
    ax.text(x_h1, 0.04, "Linear -> ReLU -> Dropout(0.3)", ha="center", va="bottom", fontsize=10)

    ax.text(x_h2, 0.96, "Hidden layer 2", ha="center", va="bottom", fontsize=13, weight="bold")
    ax.text(x_h2, 0.92, "64 perceptrons", ha="center", va="bottom", fontsize=11)
    ax.text(x_h2, 0.04, "Linear -> ReLU -> Dropout(0.3)", ha="center", va="bottom", fontsize=10)

    ax.text(x_out, 0.96, "Output layer", ha="center", va="bottom", fontsize=13, weight="bold")
    ax.text(x_out, 0.92, "1 logit", ha="center", va="bottom", fontsize=11)
    ax.text(x_out, 0.04, "Sigmoid at inference", ha="center", va="bottom", fontsize=10)

    # Training notes
    notes = (
        "Loss: BCEWithLogitsLoss    Optimizer: Adam    "
        "lr=1e-3, weight_decay=1e-4, batch_size=32, epochs=80"
    )
    ax.text(0.5, -0.02, notes, ha="center", va="top", fontsize=10, color="#333333", transform=ax.transAxes)

    ax.set_title("DL Risk Model: Tabular MLP (Perceptron View)", fontsize=16, weight="bold", pad=20)
    ax.set_xlim(0.02, 0.98)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    out = Path(__file__).resolve().parent.parent / "docs" / "dl_mlp_perceptron.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    output = render()
    print(f"wrote {output} ({output.stat().st_size} bytes)")
