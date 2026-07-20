from collections import defaultdict

from .model import Evidence, Link, Target
from .normalize import canonical_domain, canonical_handle, canonical_url
from .scoring import resolve_weights

_SEED_TYPES = ("email", "username", "name")
_ENTITY_LABELS = ("EMAIL", "HANDLE", "PERSON", "ORG")


def collect_targets(artifacts):
    """Alle im Netz gefundenen Ziele deduplizieren und ihre Quell-Seeds sammeln."""
    targets = {}
    for a in artifacts:
        seed = a["value"]
        for hit in a.get("search", []):
            url = hit.get("url", "")
            if not url:
                continue
            key = canonical_url(url)
            target = targets.setdefault(key, Target(key, "url", url))
            target.sources.append({"seed": seed, "via": "web:" + hit.get("source", ""), "url": url})
        for acc in a.get("accounts", []):
            url = acc.get("url", "")
            site = acc.get("site", "")
            key = canonical_url(url) if "://" in url else "account:" + site.lower()
            target = targets.setdefault(key, Target(key, "account", url or site))
            target.sources.append({"seed": seed, "via": "account", "url": url, "site": site})
    return list(targets.values())


def build_links(artifacts, stylometry, config):
    weights = resolve_weights(config)
    cfg = config.get("correlate", {}) or {}
    min_score = cfg.get("min_score", 0.3)
    stylometry_min = cfg.get("stylometry_min", 0.3)

    pair_ev = defaultdict(list)

    _link_stylometry(pair_ev, stylometry, weights, stylometry_min)
    _link_shared(pair_ev, _seed_domains(artifacts), weights["shared_domain"], "shared_domain", "gemeinsame Quelle")
    _link_shared(pair_ev, _seed_entities(artifacts), weights["shared_entity"], "shared_entity", "gemeinsame Entitaet")
    _link_seed_in_doc(pair_ev, artifacts, weights["seed_in_doc"])

    links = []
    for (a, b), evs in pair_ev.items():
        score = min(1.0, sum(e.weight for e in evs))
        if score >= min_score:
            links.append(Link(a, b, round(score, 3), evs))
    links.sort(key=lambda l: l.score, reverse=True)
    return links


def _add(pair_ev, a, b, evidence):
    if a == b:
        return
    pair_ev[tuple(sorted((a, b)))].append(evidence)


def _link_stylometry(pair_ev, stylometry, weights, stylometry_min):
    for pair in stylometry or []:
        sim = pair.get("similarity", 0.0)
        if sim >= stylometry_min:
            _add(pair_ev, pair["a"], pair["b"],
                 Evidence("stylometry", f"Stil-Aehnlichkeit {sim:.2f}", round(weights["stylometry"] * sim, 3)))


def _link_shared(pair_ev, seed_sets, weight, kind, label):
    seeds = list(seed_sets)
    for i in range(len(seeds)):
        for j in range(i + 1, len(seeds)):
            for item in seed_sets[seeds[i]] & seed_sets[seeds[j]]:
                detail = f"{label}: {item[1]}" if isinstance(item, tuple) else f"{label} {item}"
                _add(pair_ev, seeds[i], seeds[j], Evidence(kind, detail, weight))


def _link_seed_in_doc(pair_ev, artifacts, weight):
    seeds = [a for a in artifacts if a["type"] in _SEED_TYPES]
    for s in seeds:
        needle = s["value"].lower()
        if len(needle) < 4:
            continue
        for a in artifacts:
            if a is s:
                continue
            tokens = set()
            for e in a.get("entities", []):
                token = e.get("text", "").lower()
                tokens.add(token)
                tokens.add(canonical_handle(token))
            text = (a.get("text") or "").lower()
            if needle in tokens or needle in text:
                _add(pair_ev, s["value"], a["value"],
                     Evidence("seed_in_doc", f"'{s['value']}' erscheint in {a['value']}", weight))


def _seed_domains(artifacts):
    result = {}
    for a in artifacts:
        domains = set()
        for hit in a.get("search", []):
            if hit.get("url"):
                domains.add(canonical_domain(hit["url"]))
        for acc in a.get("accounts", []):
            url = acc.get("url", "")
            if url:
                domains.add(canonical_domain(url))
            elif acc.get("site"):
                domains.add("account:" + acc["site"].lower())
        result[a["value"]] = domains
    return result


def _seed_entities(artifacts):
    result = {}
    for a in artifacts:
        ents = set()
        for e in a.get("entities", []):
            label = e.get("label")
            if label not in _ENTITY_LABELS:
                continue
            val = e.get("text", "").lower()
            if label == "HANDLE":
                val = canonical_handle(val)
            ents.add((label, val))
        result[a["value"]] = ents
    return result
