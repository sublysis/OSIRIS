def _targets(output):
    return {t["key"]: t for t in (output.get("correlation", {}) or {}).get("targets", [])}


def _links(output):
    result = {}
    for l in (output.get("correlation", {}) or {}).get("links", []):
        result[tuple(sorted((l["a"], l["b"])))] = l
    return result


def diff_outputs(previous, current):
    prev_t, curr_t = _targets(previous), _targets(current)
    prev_l, curr_l = _links(previous), _links(current)
    return {
        "new_targets": [curr_t[k] for k in curr_t if k not in prev_t],
        "gone_targets": [prev_t[k] for k in prev_t if k not in curr_t],
        "new_links": [curr_l[k] for k in curr_l if k not in prev_l],
        "gone_links": [prev_l[k] for k in prev_l if k not in curr_l],
    }
