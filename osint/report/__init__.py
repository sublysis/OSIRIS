"""Report-Stufe (Modul 6).

- store.save_run: Run in SQLite persistieren (runs/targets/links) fuer spaetere Vergleiche.
- generate: lesbare Reports (Markdown, HTML) in report.output_dir schreiben.
JSON gibt es direkt in der CLI via --json.
"""

import os
from datetime import datetime, timezone

from .html import render_html
from .markdown import render_markdown
from .store import save_run

_RENDERERS = {"md": (render_markdown, "md"), "html": (render_html, "html")}

__all__ = ["save_run", "generate", "render_markdown", "render_html"]


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
