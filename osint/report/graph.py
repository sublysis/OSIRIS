import csv
import io
from xml.sax.saxutils import escape, quoteattr

# Scope: nodes/edges come from the --correlate result only (seed<->seed
# links). External targets found via --search (accounts, web hits) are not
# graphed as separate nodes - see "Shared Targets" in the md/html report for
# those instead.


def _artifact_types(artifacts):
    return {a["value"]: a.get("type", "unknown") for a in artifacts}


def _evidence_summary(link):
    return "; ".join(sorted({e["kind"] for e in link.get("evidence", [])}))


def render_graphml(output, meta=None):
    artifacts = output.get("artifacts", [])
    links = (output.get("correlation") or {}).get("links", [])
    types = _artifact_types(artifacts)

    node_ids = {}
    for value in types:
        node_ids.setdefault(value, f"n{len(node_ids)}")
    for link in links:
        for value in (link["a"], link["b"]):
            if value not in node_ids:
                node_ids[value] = f"n{len(node_ids)}"
                types.setdefault(value, "unknown")

    p = [
        "<?xml version='1.0' encoding='UTF-8'?>\n",
        "<graphml xmlns='http://graphml.graphdrawing.org/xmlns'>\n",
        "<key id='label' for='node' attr.name='label' attr.type='string'/>\n",
        "<key id='type' for='node' attr.name='type' attr.type='string'/>\n",
        "<key id='score' for='edge' attr.name='score' attr.type='double'/>\n",
        "<key id='evidence' for='edge' attr.name='evidence' attr.type='string'/>\n",
        "<graph id='G' edgedefault='undirected'>\n",
    ]
    for value, node_id in node_ids.items():
        p.append(
            f"<node id={quoteattr(node_id)}>"
            f"<data key='label'>{escape(value)}</data>"
            f"<data key='type'>{escape(types.get(value, 'unknown'))}</data>"
            "</node>\n"
        )
    for i, link in enumerate(links):
        p.append(
            f"<edge id={quoteattr(f'e{i}')} "
            f"source={quoteattr(node_ids[link['a']])} target={quoteattr(node_ids[link['b']])}>"
            f"<data key='score'>{link['score']}</data>"
            f"<data key='evidence'>{escape(_evidence_summary(link))}</data>"
            "</edge>\n"
        )
    p.append("</graph>\n</graphml>\n")
    return "".join(p)


def render_maltego_csv(output, meta=None):
    """Generic source/target edge list for Maltego's CSV import wizard
    (Import Graph from Table): map `source`/`target` to the entity columns,
    `source_type`/`target_type` for entity typing, and `score`/`evidence`
    as link properties. Maltego has no single fixed CSV schema - the import
    wizard maps arbitrary columns, so this is a reasonable generic layout
    rather than a format Maltego enforces.
    """
    artifacts = output.get("artifacts", [])
    links = (output.get("correlation") or {}).get("links", [])
    types = _artifact_types(artifacts)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["source", "source_type", "target", "target_type", "score", "evidence"])
    for link in links:
        writer.writerow([
            link["a"], types.get(link["a"], "unknown"),
            link["b"], types.get(link["b"], "unknown"),
            link["score"], _evidence_summary(link),
        ])
    return buf.getvalue()
