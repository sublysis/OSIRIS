from collections import defaultdict

from .model import Evidence, Link, Target
from .normalize import canonical_domain, canonical_handle, canonical_url
from .scoring import resolve_weights

_SEED_TYPES = ("email", "username", "name")
_ENTITY_LABELS = ("EMAIL", "HANDLE", "PERSON", "ORG")


def collect_targets(artifacts):
    """Deduplicate all targets found on the web and collect their source seeds."""
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
    _link_shared(pair_ev, _seed_domains(artifacts), weights["shared_domain"], "shared_domain", "shared source")
    _link_shared(pair_ev, _seed_entities(artifacts), weights["shared_entity"], "shared_entity", "shared entity")
    _link_shared(pair_ev, _seed_whois(artifacts), weights["shared_registrant"], "shared_registrant", "shared registrant")
    _link_shared(pair_ev, _seed_favicon(artifacts), weights["shared_favicon"], "shared_favicon", "shared favicon hash")
    _link_shared(pair_ev, _seed_certs(artifacts), weights["shared_cert"], "shared_cert", "shared TLS certificate")
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
                 Evidence("stylometry", f"style similarity {sim:.2f}", round(weights["stylometry"] * sim, 3)))


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
                     Evidence("seed_in_doc", f"'{s['value']}' appears in {a['value']}", weight))


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


def _seed_whois(artifacts):
    # Registrar alone is intentionally not used here: too many unrelated
    # domains share large registrars (GoDaddy, Namecheap, ...) for that to
    # be meaningful evidence - see docs/interpreting-scores.md.
    result = {}
    for a in artifacts:
        items = set()
        whois = a.get("whois") or {}
        if whois.get("ok"):
            org = whois.get("registrant_org")
            if org:
                items.add(("registrant org", org.strip().lower()))
            email = whois.get("registrant_email")
            if email:
                items.add(("registrant email", email.strip().lower()))
        result[a["value"]] = items
    return result


def _seed_favicon(artifacts):
    # A default/generic favicon (e.g. a bare web server's placeholder icon)
    # shared across unrelated sites is a known false-positive source for
    # this kind of hash matching - see docs/interpreting-scores.md.
    result = {}
    for a in artifacts:
        items = set()
        if a.get("favicon_mmh3") is not None:
            items.add(("mmh3", a["favicon_mmh3"]))
        if a.get("favicon_md5"):
            items.add(("md5", a["favicon_md5"]))
        result[a["value"]] = items
    return result


def _seed_certs(artifacts):
    # Matching on the literal crt.sh certificate id: two artifacts sharing
    # an id means the *same* certificate (SAN list) covers both domains.
    result = {}
    for a in artifacts:
        certs = a.get("certs") or {}
        ids = certs.get("certificate_ids") if certs.get("ok") else None
        result[a["value"]] = set(ids or [])
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
