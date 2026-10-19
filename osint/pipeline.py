"""Pipeline stage orchestration, extracted out of cli.py so both the CLI
and a future MCP server can drive the same logic. No print()/argparse here -
callers render outcomes however fits their interface (stdout vs. MCP
tool-call return value).
"""

from osint.certs import CertClient
from osint.correlate import correlate
from osint.correlate.normalize import canonical_domain
from osint.fetcher import Fetcher
from osint.input_parser import ArtifactType
from osint.localfiles import LocalFileLoader
from osint.monitor import compare_to_previous
from osint.nlp import (
    EntityExtractor,
    KeyphraseExtractor,
    StylometryModel,
    basic_features,
    extract_regex_entities,
)
from osint.search import SearchError, get_provider
from osint.search.tools import HoleheWrapper, MaigretWrapper
from osint.whois import WhoisClient


def fetch_urls(url_artifacts, config, results):
    if not url_artifacts:
        return []
    fetcher = Fetcher(config)
    by_value = {r["value"]: r for r in results}
    outcomes = []
    for art in url_artifacts:
        res = fetcher.fetch(art.value)
        entry = by_value.get(art.value, {})
        if res.ok and res.text:
            entry["title"] = res.title
            entry["text"] = res.text
            entry["chars"] = len(res.text)
            if res.favicon_mmh3 is not None or res.favicon_md5 is not None:
                entry["favicon_url"] = res.favicon_url
                entry["favicon_mmh3"] = res.favicon_mmh3
                entry["favicon_md5"] = res.favicon_md5
            outcomes.append({"value": art.value, "ok": True, "status": res.status, "chars": len(res.text)})
        else:
            entry["error"] = res.error or f"HTTP {res.status}"
            outcomes.append({"value": art.value, "ok": False, "error": entry["error"]})
    return outcomes


def load_local_files(file_artifacts, case_dir, config, results):
    if not file_artifacts:
        return []
    loader = LocalFileLoader(config)
    by_value = {r["value"]: r for r in results}
    outcomes = []
    for art in file_artifacts:
        res = loader.load(case_dir, art.value)
        entry = by_value.get(art.value, {})
        if res.ok and res.text:
            entry["title"] = res.title
            entry["text"] = res.text
            entry["chars"] = len(res.text)
            outcomes.append({"value": art.value, "ok": True, "chars": len(res.text)})
        else:
            entry["error"] = res.error
            outcomes.append({"value": art.value, "ok": False, "error": res.error})
    return outcomes


def run_whois(url_artifacts, config, results):
    if not url_artifacts:
        return []
    client = WhoisClient(config)
    by_value = {r["value"]: r for r in results}
    outcomes = []
    for art in url_artifacts:
        domain = canonical_domain(art.value)
        result = client.lookup(domain)
        entry = by_value.get(art.value, {})
        entry["whois"] = result.to_dict()
        if result.ok:
            if result.registrant_org or result.registrant_email:
                note = ""
            elif result.redacted:
                note = " (registrant redacted)"
            else:
                note = " (no registrant data)"
            outcomes.append({
                "value": art.value, "domain": domain, "ok": True,
                "registrar": result.registrar, "note": note,
            })
        else:
            outcomes.append({
                "value": art.value, "domain": domain, "ok": False, "error": result.error,
            })
    return outcomes


def run_certs(url_artifacts, config, results):
    if not url_artifacts:
        return []
    client = CertClient(config)
    by_value = {r["value"]: r for r in results}
    outcomes = []
    for art in url_artifacts:
        domain = canonical_domain(art.value)
        result = client.lookup(domain)
        entry = by_value.get(art.value, {})
        entry["certs"] = result.to_dict()
        if result.ok:
            outcomes.append({
                "value": art.value, "domain": domain, "ok": True,
                "cert_count": result.cert_count, "subdomains": len(result.subdomains),
            })
        else:
            outcomes.append({
                "value": art.value, "domain": domain, "ok": False, "error": result.error,
            })
    return outcomes


def run_nlp(results, config):
    docs = [r for r in results if r.get("text")]
    if not docs:
        return None, {"docs": 0}
    ner_report = _nlp_entities_keyphrases(docs, config)
    stylometry, style_report = _nlp_stylometry(docs, config)
    return stylometry, {"docs": len(docs), **ner_report, **style_report}


def _nlp_entities_keyphrases(docs, config):
    cfg = config.get("nlp", {})
    ner = EntityExtractor(cfg.get("spacy_model", "de_core_news_lg"))
    kp = KeyphraseExtractor(lang=cfg.get("keyphrase_lang", "de"), top=cfg.get("keyphrase_top", 20))
    ner_ok, kp_ok = True, True
    ner_error = None
    kp_error = None
    per_doc = []

    for d in docs:
        text = d["text"]
        try:
            ents = ner.extract(text, use_spacy=ner_ok)
        except RuntimeError as e:
            ner_error = str(e)
            ner_ok = False
            ents = extract_regex_entities(text)
        d["entities"] = [{"label": e.label, "text": e.text} for e in ents]

        if kp_ok:
            try:
                d["keyphrases"] = [{"text": k.text, "score": round(k.score, 4)} for k in kp.extract(text)]
            except RuntimeError as e:
                kp_error = str(e)
                kp_ok = False

        per_doc.append({
            "value": d["value"],
            "entities": len(d.get("entities", [])),
            "keyphrases": len(d.get("keyphrases", [])),
        })

    return {"ner_error": ner_error, "keyphrase_error": kp_error, "per_doc": per_doc}


def _nlp_stylometry(docs, config):
    for d in docs:
        d["style"] = {k: round(v, 5) for k, v in basic_features(d["text"]).items()}

    if len(docs) < 2:
        return [], {"stylometry_skipped": "needs >=2 texts"}

    labels = [d["value"] for d in docs]
    threshold = config.get("nlp", {}).get("stylometry_threshold", 0.0)
    try:
        model = StylometryModel().fit([d["text"] for d in docs], labels)
    except RuntimeError as e:
        return None, {"stylometry_error": str(e)}

    pairs = model.most_similar_pairs(threshold=threshold)
    stylometry = [{"a": a, "b": b, "similarity": round(score, 4)} for a, b, score in pairs]
    return stylometry, {"stylometry_pairs": pairs}


def run_search(groups, config, results, provider_name, limit):
    by_value = {r["value"]: r for r in results}
    outcomes = {"provider_error": None, "provider_name": None, "web": [], "tools": []}

    try:
        provider = get_provider(config, provider_name)
    except SearchError as e:
        outcomes["provider_error"] = str(e)
        provider = None

    queries = []
    for art_type, fmt in ((ArtifactType.NAME, '"{}"'), (ArtifactType.EMAIL, '"{}"'), (ArtifactType.USERNAME, "{}")):
        for a in groups.get(art_type, []):
            queries.append((a.value, fmt.format(a.value)))

    if provider is not None and queries:
        outcomes["provider_name"] = provider.name
        outcomes["query_count"] = len(queries)
        for value, query in queries:
            try:
                hits = provider.search(query, limit=limit)
            except SearchError as e:
                outcomes["web_skipped"] = str(e)
                break
            entry = by_value.get(value, {})
            entry.setdefault("search", []).extend(h.to_dict() for h in hits)
            outcomes["web"].append({"value": value, "hits": len(hits)})

    outcomes["tools"].append(_run_tool(MaigretWrapper(), groups.get(ArtifactType.USERNAME, []), by_value))
    outcomes["tools"].append(_run_tool(HoleheWrapper(), groups.get(ArtifactType.EMAIL, []), by_value))
    return outcomes


def _run_tool(tool, artifacts, by_value):
    if not artifacts:
        return {"name": tool.name, "binary": tool.binary, "status": "noop", "targets": 0}
    if not tool.available():
        return {"name": tool.name, "binary": tool.binary, "status": "unavailable", "targets": len(artifacts)}
    per_target = []
    for a in artifacts:
        res = tool.run(a.value)
        entry = by_value.get(a.value, {})
        entry.setdefault("accounts", []).extend(res.hits)
        per_target.append({"value": a.value, "hits": len(res.hits), "error": res.error})
    return {
        "name": tool.name, "binary": tool.binary, "status": "ran",
        "targets": len(artifacts), "per_target": per_target,
    }


def run_correlate(results, stylometry, config):
    return correlate(results, stylometry, config)


def run_monitor(config, output, input_name):
    return compare_to_previous(config, output, input_name)
