"""Render a markdown doc to PDF.

Pure-Python pipeline (markdown -> HTML -> PDF via xhtml2pdf) so no native
binaries are required. Run from project root:

    python scripts/render_paper.py                      # renders the synthesis paper
    python scripts/render_paper.py presentation_outline # renders the presentation deck

Dependencies (install temporarily, not pinned in requirements.txt):
    pip install markdown xhtml2pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

import markdown
from xhtml2pdf import pisa

ROOT = Path(__file__).resolve().parent.parent

TARGETS = {
    "paper": ("Reflective_Synthesis_Paper.md", "Reflective_Synthesis_Paper.pdf"),
    "presentation_outline": ("presentation_outline.md", "presentation_outline.pdf"),
}

CSS = """
@page { size: letter; margin: 0.9in 0.8in; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #111; }
h1 { font-size: 18pt; margin-top: 0.4em; }
h2 { font-size: 13pt; margin-top: 1.2em; border-bottom: 1px solid #888; padding-bottom: 2px; }
h3 { font-size: 11.5pt; margin-top: 1em; }
code { font-family: Consolas, monospace; font-size: 9.5pt; background: #f3f3f3; padding: 1px 3px; }
pre { background: #f3f3f3; padding: 6px; font-size: 9pt; }
table { border-collapse: collapse; margin: 0.5em 0; }
th, td { border: 1px solid #888; padding: 4px 8px; font-size: 9.5pt; }
th { background: #eee; }
blockquote { border-left: 3px solid #888; margin-left: 0; padding-left: 10px; color: #444; }
hr { border: none; border-top: 1px solid #888; }
"""


def render(target: str) -> None:
    src_name, dst_name = TARGETS[target]
    src = ROOT / "docs" / src_name
    dst = ROOT / "docs" / dst_name
    md_text = src.read_text(encoding="utf-8")
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    html = f"<html><head><style>{CSS}</style></head><body>{html_body}</body></html>"
    with dst.open("wb") as f:
        result = pisa.CreatePDF(html, dest=f, encoding="utf-8")
    if result.err:
        raise SystemExit(f"PDF render failed with {result.err} errors")
    print(f"Wrote {dst} ({dst.stat().st_size} bytes)")


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "paper"
    if target not in TARGETS:
        raise SystemExit(f"Unknown target {target!r}; choose from {list(TARGETS)}")
    render(target)


if __name__ == "__main__":
    main()
