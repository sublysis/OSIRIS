from html import escape

_CSS = """
body{font-family:system-ui,Arial,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1b1b1b}
h1{border-bottom:2px solid #333;padding-bottom:.3rem}
h2{margin-top:2rem;color:#0b5}
table{border-collapse:collapse;width:100%;margin:.5rem 0}
th,td{border:1px solid #ddd;padding:.4rem .6rem;text-align:left}
th{background:#f4f4f4}
.badge{background:#0b5;color:#fff;border-radius:10px;padding:0 .5rem;font-size:.8rem}
.link{border-left:3px solid #0b5;padding:.3rem .8rem;margin:.5rem 0;background:#fafafa}
code{background:#f0f0f0;padding:.1rem .3rem;border-radius:3px}
"""


def _counts(artifacts):
    counts = {}
    for a in artifacts:
        counts[a["type"]] = counts.get(a["type"], 0) + 1
    return counts


def render_html(output, meta=None):
    meta = meta or {}
    artifacts = output.get("artifacts", [])
    corr = output.get("correlation", {}) or {}
    p = [
        "<!doctype html><html lang='de'><head><meta charset='utf-8'>",
        "<title>OSINT-Report</title><style>", _CSS, "</style></head><body>",
        "<h1>OSINT-Report</h1>",
    ]

    meta_rows = []
    for label, key in (("Eingabe", "input"), ("Erstellt", "created_at"), ("Run-ID", "run_id")):
        if meta.get(key):
            meta_rows.append(f"<li>{label}: <code>{escape(str(meta[key]))}</code></li>")
    if meta_rows:
        p.append("<ul>" + "".join(meta_rows) + "</ul>")

    p.append("<h2>Artefakte</h2><table><tr><th>Typ</th><th>Anzahl</th></tr>")
    for k, v in _counts(artifacts).items():
        p.append(f"<tr><td>{escape(k)}</td><td>{v}</td></tr>")
    p.append("</table>")

    shared = [t for t in corr.get("targets", []) if t.get("seed_count", 0) >= 2]
    if shared:
        p.append("<h2>Geteilte Ziele (&ge;2 Selektoren)</h2><table><tr><th>Ziel</th><th>Seeds</th></tr>")
        for t in shared:
            seeds = escape(", ".join(sorted({s["seed"] for s in t.get("sources", [])})))
            p.append(
                f"<tr><td>{escape(t['value'])} <span class='badge'>{t['seed_count']}</span></td><td>{seeds}</td></tr>"
            )
        p.append("</table>")

    links = corr.get("links", [])
    if links:
        p.append("<h2>Verknuepfungen</h2>")
        for l in links:
            p.append(f"<div class='link'><b>{l['score']:.2f}</b> {escape(l['a'])} &harr; {escape(l['b'])}<ul>")
            for e in l.get("evidence", []):
                p.append(f"<li>{escape(e['kind'])}: {escape(e['detail'])}</li>")
            p.append("</ul></div>")

    mon = output.get("monitor")
    if mon:
        p.append(f"<h2>Aenderungen seit Run #{escape(str(mon.get('previous_run_id')))}</h2><ul>")
        p.append(f"<li>Neue Ziele: {len(mon.get('new_targets', []))}</li>")
        for t in mon.get("new_targets", []):
            p.append(f"<li>&plus; {escape(t['value'])}</li>")
        p.append(f"<li>Neue Verknuepfungen: {len(mon.get('new_links', []))}</li>")
        for l in mon.get("new_links", []):
            p.append(f"<li>&plus; {l['score']:.2f} {escape(l['a'])} &harr; {escape(l['b'])}</li>")
        p.append("</ul>")

    docs = [a for a in artifacts if a.get("text")]
    if docs:
        p.append("<h2>Dokumente</h2>")
        for d in docs:
            p.append(f"<h3>{escape(d['value'])}</h3><ul>")
            if d.get("title"):
                p.append(f"<li>Titel: {escape(d['title'])}</li>")
            if d.get("chars"):
                p.append(f"<li>Zeichen: {d['chars']}</li>")
            ents = d.get("entities", [])
            if ents:
                p.append("<li>Entitaeten: " + escape(", ".join(f"{e['text']} ({e['label']})" for e in ents[:15])) + "</li>")
            kps = d.get("keyphrases", [])
            if kps:
                p.append("<li>Keyphrases: " + escape(", ".join(k["text"] for k in kps[:12])) + "</li>")
            p.append("</ul>")

    p.append("</body></html>")
    return "".join(p)
