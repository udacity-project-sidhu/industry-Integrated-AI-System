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

MERMAID = """%%{init: {'theme':'default', 'themeVariables':{'fontSize':'18px','lineColor':'#333','clusterBkg':'#fafafa','clusterBorder':'#888'}, 'flowchart':{'curve':'basis','nodeSpacing':60,'rankSpacing':70,'padding':12}}}%%
flowchart LR
    X[Input features<br/>shape: batch x input_dim] --> L1[Linear<br/>input_dim to 64]
    L1 --> A1[ReLU]
    A1 --> D1[Dropout p=0.3]
    D1 --> L2[Linear<br/>64 to 64]
    L2 --> A2[ReLU]
    A2 --> D2[Dropout p=0.3]
    D2 --> O[Linear<br/>64 to 1 logit]

    O --> I[Sigmoid<br/>inference only]
    I --> P[Predicted risk probability]

    Y[True label y in {0,1}] --> LOSS[BCEWithLogitsLoss]
    O --> LOSS

    subgraph TRAINING[Training setup]
        direction TB
        OPT[Adam optimizer]
        HP[lr=1e-3\nweight_decay=1e-4\nbatch_size=32\nepochs=80]
    end

    HP -. controls .-> OPT
    HP -. controls .-> LOSS
    OPT -. updates .-> L1
    OPT -. updates .-> L2
    OPT -. updates .-> O

    classDef model fill:#e3f2fd,stroke:#1976d2,color:#000
    classDef train fill:#fff3e0,stroke:#ef6c00,color:#000
    classDef loss fill:#ffebee,stroke:#c62828,color:#000
    classDef io fill:#f1f8e9,stroke:#558b2f,color:#000
    class X,Y,P io
    class L1,A1,D1,L2,A2,D2,O,I model
    class OPT,HP train
    class LOSS loss
"""


def render() -> None:
    payload = {"code": MERMAID, "mermaid": {"theme": "default"}}
    raw = json.dumps(payload).encode("utf-8")
    compressed = zlib.compress(raw, 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    url = f"https://mermaid.ink/img/pako:{encoded}?type=png&bgColor=FFFFFF"
    out = Path(__file__).resolve().parent.parent / "docs" / "dl_mlp_architecture.png"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    print(f"URL: {url}"); with urlopen(req, timeout=60) as r:
        out.write_bytes(r.read())
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    render()
