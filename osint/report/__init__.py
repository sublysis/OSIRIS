"""Report stage (module 6).

- store.save_run: persist run in SQLite (runs/targets/links) for later comparisons.
- generate: write human-readable reports (Markdown, HTML) to report.output_dir.
  Also supports graph export (`graphml`, `maltego`) of the --correlate link
  network - opt-in via `--report md,html,graphml,maltego`, not part of the
  default format list.
JSON is available directly in the CLI via --json.
"""

import os
from datetime import datetime, timezone

from .graph import render_graphml, render_maltego_csv
from .html import render_html
from .markdown import render_markdown
from .store import save_run

_RENDERERS = {
    "md": (render_markdown, "md"),
    "html": (render_html, "html"),
    "graphml": (render_graphml, "graphml"),
    "maltego": (render_maltego_csv, "csv"),
}

__all__ = [
    "save_run", "generate", "render_markdown", "render_html", "render_graphml", "render_maltego_csv",
]


def generate(output, config, input_name=None, formats=("md", "html"), run_id=None, out_dir=None):
    report_cfg = config.get("report", {}) or {}
    out_dir = out_dir or report_cfg.get("output_dir", "reports")
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    meta = {
        "input": input_name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_id,
    }

    written = {}
    for fmt in formats:
        renderer = _RENDERERS.get(fmt)
        if renderer is None:
            continue
        render, ext = renderer
        path = os.path.join(out_dir, f"report_{ts}.{ext}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(output, meta))
        written[fmt] = path
    return written
