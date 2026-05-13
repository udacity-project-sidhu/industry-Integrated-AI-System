"""Render docs/architecture.png from the mermaid source.

Uses the public mermaid.ink service (no local Node.js dependency).
Run from project root:
    python scripts/render_architecture.py
"""
from __future__ import annotations

import base64
import json
import zlib
from pathlib import Path
from urllib.request import Request, urlopen

MERMAID = """%%{init: {'theme':'default', 'themeVariables':{'fontSize':'18px','lineColor':'#333','clusterBkg':'#fafafa','clusterBorder':'#888'}, 'flowchart':{'curve':'basis','nodeSpacing':60,'rankSpacing':70,'padding':12}}}%%
flowchart TD
    ENTRY[Demo invocation<br/>run_all.py step 6 / notebook 05<br/>picks 3 demo patients + fixed clinician request<br/><i>run_all.py</i>] --> A
    A[Patient record<br/>UCI Heart Disease<br/><i>src/data_loader.py</i>] --> B[Preprocessing<br/>log1p + StandardScaler + one-hot<br/><i>src/preprocessing.py</i>]

    subgraph SCORING[Deterministic scoring]
        direction LR
        C[ML model<br/>HistGradientBoosting<br/><i>src/ml_model.py</i>]
        D[DL model<br/>PyTorch MLP<br/><i>src/dl_model.py</i>]
        E[Ensemble + tier + confidence flag<br/><i>src/decision.py</i>]
        C --> E
        D --> E
    end

    B --> C
    B --> D

    E --> F[Agent orchestrator<br/>plan / retrieve / explain / evaluate / revise<br/><i>src/agent_orchestrator.py</i>]

    subgraph INGEST[RAG ingestion - build time, idempotent]
        direction LR
        P[knowledge_base/*.md<br/>clinical guideline markdown]
        Q[Header-aware chunker<br/>split on H1/H2, max 1500 chars<br/><i>src/rag/knowledge_base.py</i>]
        R[OpenAI embeddings<br/>text-embedding-3-small<br/><i>src/rag/embeddings.py</i>]
        S[ChromaDB persistent<br/>HNSW + SQLite<br/><i>src/rag/vector_store.py</i>]
        T[sha256 manifest<br/>ingest_manifest.json<br/><i>src/rag/manifest.py</i>]
        P --> Q --> R --> S
        P -. hash check .-> T
        T -. skip unchanged .-> R
    end

    subgraph AGENTIC[Agentic loop - query time]
        direction LR
        G[RAG retriever<br/>top-k cosine over ChromaDB<br/><i>src/rag/retriever.py</i>]
        H[GenAI explainer<br/>OpenAI LLM + bracketed citations<br/><i>src/genai_explainer.py</i>]
        J[Evaluator-critic<br/>pass / score / issues<br/><i>src/agent_orchestrator.py</i>]
    end

    S -. read .-> G
    F --> G --> H
    H --> J
    J -. revise loop .-> H

    subgraph SAFETY[Safety side-channel]
        K[Refusal substring list + caps<br/><i>src/safeguards.py</i>]
    end
    F -. guardrail check .-> K

    H --> L[Clinician-facing explanation]
    K -. refusal .-> L

    subgraph AUDIT[Audit trail]
        direction LR
        M[outputs/run_log.jsonl<br/>append-only events<br/><i>src/agent_orchestrator.py</i>]
        N[docs/transcripts/<br/>per-run markdown<br/><i>src/transcripts.py</i>]
    end

    F -. log every event .-> M
    L -. persist .-> N

    classDef det fill:#e3f2fd,stroke:#1976d2,color:#000
    classDef llm fill:#f3e5f5,stroke:#7b1fa2,color:#000
    classDef safe fill:#ffebee,stroke:#c62828,color:#000
    classDef audit fill:#f1f8e9,stroke:#558b2f,color:#000
    classDef ingest fill:#fff3e0,stroke:#ef6c00,color:#000
    classDef entry fill:#fffde7,stroke:#f9a825,color:#000
    class A,B,C,D,E det
    class G,H,J llm
    class K safe
    class M,N audit
    class P,Q,R,S,T ingest
    class ENTRY entry
"""


def render() -> None:
    payload = {"code": MERMAID, "mermaid": {"theme": "default"}}
    raw = json.dumps(payload).encode("utf-8")
    compressed = zlib.compress(raw, 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    url = f"https://mermaid.ink/img/pako:{encoded}?type=png&bgColor=FFFFFF"
    out = Path(__file__).resolve().parent.parent / "docs" / "architecture.png"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as r:
        out.write_bytes(r.read())
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    render()
