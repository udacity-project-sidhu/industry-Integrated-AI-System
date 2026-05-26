"""Save an agent `RunResult` as a human-readable markdown transcript for auditing."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .agent_orchestrator import RunResult


def save_transcript(result: RunResult, label: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{label}_{result.run_id}.md"
    path = out_dir / fname

    lines: list[str] = []
    lines.append(f"# Run transcript - {label}")
    lines.append("")
    lines.append(f"- run_id: `{result.run_id}`")
    lines.append(f"- timestamp: {datetime.utcnow().isoformat()}Z")
    lines.append(f"- refused: `{result.refused}`")
    if result.refusal_reason:
        lines.append(f"- refusal_reason: {result.refusal_reason}")
    lines.append(f"- revised: `{result.revised}`")
    lines.append("")

    if result.score is not None:
        lines.append("## Patient score")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(result.score, indent=2))
        lines.append("```")
        lines.append("")

    if result.evaluation is not None:
        lines.append("## Evaluator verdict")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(result.evaluation, indent=2))
        lines.append("```")
        lines.append("")

    if result.explanation is not None:
        lines.append("## Final explanation")
        lines.append("")
        lines.append(result.explanation.get("text", ""))
        lines.append("")
        lines.append(f"- cited indices: {result.explanation.get('cited_indices')}")
        lines.append(f"- cited sources: {result.explanation.get('cited_sources')}")
        lines.append(f"- model: {result.explanation.get('model')}")
        lines.append("")

    lines.append("## Event log")
    lines.append("")
    for ev in result.events:
        event = ev.get("event")
        lines.append(f"### {event}")
        lines.append("")
        lines.append("```json")
        payload = {k: v for k, v in ev.items() if k not in ("event", "ts", "run_id")}
        lines.append(json.dumps(payload, indent=2, default=str))
        lines.append("```")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
