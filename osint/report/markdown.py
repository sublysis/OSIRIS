def _counts(artifacts):
    counts = {}
    for a in artifacts:
        counts[a["type"]] = counts.get(a["type"], 0) + 1
    return counts


def render_markdown(output, meta=None):
    meta = meta or {}
    artifacts = output.get("artifacts", [])
    corr = output.get("correlation", {}) or {}
    lines = ["# OSINT-Report", ""]

    for label, key in (("Eingabe", "input"), ("Erstellt", "created_at"), ("Run-ID", "run_id")):
        if meta.get(key):
            lines.append(f"- {label}: `{meta[key]}`")
    lines.append("")

    lines.append("## Artefakte")
    for k, v in _counts(artifacts).items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    shared = [t for t in corr.get("targets", []) if t.get("seed_count", 0) >= 2]
    if shared:
        lines.append("## Geteilte Ziele (>=2 Selektoren)")
        for t in shared:
            seeds = ", ".join(sorted({s["seed"] for s in t.get("sources", [])}))
            lines.append(f"- **{t['value']}** ({t['seed_count']}) <- {seeds}")
        lines.append("")

    links = corr.get("links", [])
    if links:
        lines.append("## Verknuepfungen")
        for l in links:
            lines.append(f"- **{l['score']:.2f}** {l['a']} <-> {l['b']}")
            for e in l.get("evidence", []):
                lines.append(f"    - {e['kind']}: {e['detail']}")
        lines.append("")

    mon = output.get("monitor")
    if mon:
        lines.append(f"## Aenderungen seit Run #{mon.get('previous_run_id')}")
        lines.append(f"- Neue Ziele: {len(mon.get('new_targets', []))}")
        for t in mon.get("new_targets", []):
            lines.append(f"    - {t['value']}")
        lines.append(f"- Neue Verknuepfungen: {len(mon.get('new_links', []))}")
        for l in mon.get("new_links", []):
            lines.append(f"    - {l['score']:.2f} {l['a']} <-> {l['b']}")
        lines.append("")

    docs = [a for a in artifacts if a.get("text")]
    if docs:
        lines.append("## Dokumente")
        for d in docs:
            lines.append(f"### {d['value']}")
            if d.get("title"):
                lines.append(f"- Titel: {d['title']}")
            if d.get("chars"):
                lines.append(f"- Zeichen: {d['chars']}")
            ents = d.get("entities", [])
            if ents:
                lines.append("- Entitaeten: " + ", ".join(f"{e['text']} ({e['label']})" for e in ents[:15]))
            kps = d.get("keyphrases", [])
            if kps:
                lines.append("- Keyphrases: " + ", ".join(k["text"] for k in kps[:12]))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
