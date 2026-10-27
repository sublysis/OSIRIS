from html import escape

_CSS = """
body{font-family:system-ui,Arial,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1b1b1b}
h1{border-bottom:2px solid #333;padding-bottom:.3rem}
h2{margin-top:2rem;color:#40859c}
table{border-collapse:collapse;width:100%;margin:.5rem 0}
th,td{border:1px solid #ddd;padding:.4rem .6rem;text-align:left}
th{background:#f4f4f4}
.badge{background:#40859c;color:#fff;border-radius:10px;padding:0 .5rem;font-size:.8rem}
.link{border-left:3px solid #40859c;padding:.3rem .8rem;margin:.5rem 0;background:#fafafa}
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
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<title>Vallanx Stylometric OSINT-Report</title><style>", _CSS, "</style></head><body>",
        "<h1>Vallanx Stylomentric OSINT-Report</h1>",
    ]

    meta_rows = []
    for label, key in (("Input", "input"), ("Created", "created_at"), ("Run-ID", "run_id")):
        if meta.get(key):
            meta_rows.append(f"<li>{label}: <code>{escape(str(meta[key]))}</code></li>")
    if meta_rows:
        p.append("<ul>" + "".join(meta_rows) + "</ul>")

    p.append("<h2>Artefacts</h2><table><tr><th>Type</th><th>Count</th></tr>")
    for k, v in _counts(artifacts).items():
        p.append(f"<tr><td>{escape(k)}</td><td>{v}</td></tr>")
    p.append("</table>")

    whois_entries = [a for a in artifacts if a.get("whois")]
    if whois_entries:
        p.append(
            "<h2>WHOIS</h2><table><tr><th>URL</th><th>Domain</th><th>Registrar</th>"
            "<th>Registrant Org</th><th>Created</th><th>Expires</th></tr>"
        )
        for a in whois_entries:
            w = a["whois"]
            if not w.get("ok"):
                p.append(
                    f"<tr><td>{escape(a['value'])}</td><td colspan='5'>error: {escape(w.get('error') or '')}</td></tr>"
                )
                continue
            registrant = w.get("registrant_org") or "(redacted/absent)"
            p.append(
                "<tr>"
                f"<td>{escape(a['value'])}</td>"
                f"<td>{escape(w.get('domain') or '')}</td>"
                f"<td>{escape(w.get('registrar') or '')}</td>"
                f"<td>{escape(registrant)}</td>"
                f"<td>{escape(w.get('created') or '')}</td>"
                f"<td>{escape(w.get('expires') or '')}</td>"
                "</tr>"
            )
        p.append("</table>")

    cert_entries = [a for a in artifacts if a.get("certs")]
    if cert_entries:
        p.append(
            "<h2>Certificate Transparency</h2><table><tr><th>URL</th><th>Domain</th>"
            "<th>Certs</th><th>Subdomains</th></tr>"
        )
        for a in cert_entries:
            c = a["certs"]
            if not c.get("ok"):
                p.append(
                    f"<tr><td>{escape(a['value'])}</td><td colspan='3'>error: {escape(c.get('error') or '')}</td></tr>"
                )
                continue
            subdomains = escape(", ".join(c.get("subdomains", [])[:15]))
            p.append(
                "<tr>"
                f"<td>{escape(a['value'])}</td>"
                f"<td>{escape(c.get('domain') or '')}</td>"
                f"<td>{c.get('cert_count', 0)}</td>"
                f"<td>{subdomains}</td>"
                "</tr>"
            )
        p.append("</table>")

    shared = [t for t in corr.get("targets", []) if t.get("seed_count", 0) >= 2]
    if shared:
        p.append("<h2>Shared Targets (&ge;2 Selectors)</h2><table><tr><th>Target</th><th>Seeds</th></tr>")
        for t in shared:
            seeds = escape(", ".join(sorted({s["seed"] for s in t.get("sources", [])})))
            p.append(
                f"<tr><td>{escape(t['value'])} <span class='badge'>{t['seed_count']}</span></td><td>{seeds}</td></tr>"
            )
        p.append("</table>")

    links = corr.get("links", [])
    if links:
        p.append("<h2>Linked Evidence</h2>")
        for l in links:
            p.append(f"<div class='link'><b>{l['score']:.2f}</b> {escape(l['a'])} &harr; {escape(l['b'])}<ul>")
            for e in l.get("evidence", []):
                p.append(f"<li>{escape(e['kind'])}: {escape(e['detail'])}</li>")
            p.append("</ul></div>")

    mon = output.get("monitor")
    if mon:
        p.append(f"<h2>Changes since prev. run #{escape(str(mon.get('previous_run_id')))}</h2><ul>")
        p.append(f"<li>New Targets: {len(mon.get('new_targets', []))}</li>")
        for t in mon.get("new_targets", []):
            p.append(f"<li>&plus; {escape(t['value'])}</li>")
        p.append(f"<li>New Links: {len(mon.get('new_links', []))}</li>")
        for l in mon.get("new_links", []):
            p.append(f"<li>&plus; {l['score']:.2f} {escape(l['a'])} &harr; {escape(l['b'])}</li>")
        p.append("</ul>")

    docs = [a for a in artifacts if a.get("text")]
    if docs:
        p.append("<h2>Documents</h2>")
        for d in docs:
            p.append(f"<h3>{escape(d['value'])}</h3><ul>")
            if d.get("title"):
                p.append(f"<li>Title: {escape(d['title'])}</li>")
            if d.get("chars"):
                p.append(f"<li>Characters: {d['chars']}</li>")
            if d.get("favicon_mmh3") is not None or d.get("favicon_md5"):
                fav = f"mmh3 {d.get('favicon_mmh3')}" if d.get("favicon_mmh3") is not None else "mmh3 n/a"
                fav += f", md5 {d.get('favicon_md5')}" if d.get("favicon_md5") else ""
                p.append(f"<li>Favicon: {escape(fav)}</li>")
            ents = d.get("entities", [])
            if ents:
                p.append("<li>Entities: " + escape(", ".join(f"{e['text']} ({e['label']})" for e in ents[:15])) + "</li>")
            kps = d.get("keyphrases", [])
            if kps:
                p.append("<li>Keyphrases: " + escape(", ".join(k["text"] for k in kps[:12])) + "</li>")
            p.append("</ul>")

    p.append("</body></html>")
    return "".join(p)