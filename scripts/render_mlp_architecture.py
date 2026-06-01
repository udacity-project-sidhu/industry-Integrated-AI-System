"""Render docs/dl_mlp_architecture.png from Mermaid source.

Uses the public mermaid.ink service (no local Node.js dependency).
Run from project root:
    python scripts/render_mlp_architecture.py
"""
from __future__ import annotations

import base64
import json
import zlib
from pathlib import Path
from urllib.request import Request, urlopen

MERMAID = """%%{init: {'theme':'default', 'themeVariables':{'fontSize':'17px','lineColor':'#333','clusterBkg':'#fafafa','clusterBorder':'#888'}, 'flowchart':{'curve':'linear','nodeSpacing':40,'rankSpacing':55,'padding':10}}}%%
flowchart LR
    subgraph IN[Input layer]
        direction TB
        x1((x1))
        x2((x2))
        x3((x3))
        xd((...))
        xn((xn))
    end

    subgraph H1[Hidden layer 1: 64 perceptrons]
        direction TB
        h11((h1_1))
        h12((h1_2))
        h1d((...))
        h1n((h1_64))
        a1[ReLU + Dropout 0.3]
    end

    subgraph H2[Hidden layer 2: 64 perceptrons]
        direction TB
        h21((h2_1))
        h22((h2_2))
        h2d((...))
        h2n((h2_64))
        a2[ReLU + Dropout 0.3]
    end

    subgraph OUT[Output]
        direction TB
        z((logit z))
        p((p = sigmoid(z)))
    end

    note1[Each perceptron computes w dot x + b]
    note2[Fully connected between adjacent layers]
    train[Adam lr=1e-3, wd=1e-4, batch=32, epochs=80]
    loss[BCEWithLogitsLoss on z]

    x1 --> h11
    x1 --> h12
    x2 --> h11
    x2 --> h12
    x3 --> h12
    xn --> h1n
    xd -. many edges omitted .- h1d

    h11 --> a1
    h12 --> a1
    h1n --> a1
    h1d -. many edges omitted .- a1

    a1 --> h21
    a1 --> h22
    a1 --> h2n
    a1 --> h2d

    h21 --> a2
    h22 --> a2
    h2n --> a2
    h2d -. many edges omitted .- a2

    a2 --> z --> p
    z --> loss
    train -. optimizes .-> loss

    note1 -. describes .-> h11
    note2 -. applies to .-> h21

    classDef neuron fill:#e3f2fd,stroke:#1976d2,color:#000
    classDef block fill:#fff3e0,stroke:#ef6c00,color:#000
    classDef text fill:#f1f8e9,stroke:#558b2f,color:#000
    classDef crit fill:#ffebee,stroke:#c62828,color:#000
    class x1,x2,x3,xd,xn,h11,h12,h1d,h1n,h21,h22,h2d,h2n,z,p neuron
    class a1,a2,train block
    class note1,note2 text
    class loss crit
"""


def render() -> None:
    payload = {"code": MERMAID, "mermaid": {"theme": "default"}}
    raw = json.dumps(payload).encode("utf-8")
    compressed = zlib.compress(raw, 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    url = f"https://mermaid.ink/img/pako:{encoded}?type=png&bgColor=FFFFFF"
    out = Path(__file__).resolve().parent.parent / "docs" / "dl_mlp_architecture.png"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as r:
        out.write_bytes(r.read())
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    render()
