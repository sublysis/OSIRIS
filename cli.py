#!/usr/bin/env python3

"""
OSINT Stylometric Search

Last updated: 10/2026

GitHub Issues: https://github.com/sublysis/osint_stylometric_search/issues
Author: Laurent Schueller, https://sublysis.github.io
License: European Union Public Licence (EUPL) v1.2

For authorized penetration testing and network auditing use only.
"""

import argparse
import json
import os
import sys

from osint import pipeline
from osint.config import load_config
from osint.input_parser import ArtifactType, group_by_type, parse_file

# ASCII HEADER
# https://patorjk.com/software/taag/#p=display&f=TIC&t=OSINT+Stylo+Search&x=none&v=4&h=4&w=80&we=false&ft=thedraw
ascii_header = '''
[0;37;40m ▄▄▄▄▄▄▄▄▄    ▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄   ▄▄▄▄▄▄▄▄▄▄       ▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄ ▄▄▄▄   ▄▄▄▄  ▄▄▄▄          ▄▄▄▄▄▄▄▄▄         ▄▄▄▄▄▄▄▄▄▄   ▄▄▄▄▄▄▄▄▄▄   ▄▄▄▄▄▄▄▄▄   ▄▄▄▄▄▄▄▄▄▄    ▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄   ▄▄▄▄ [0m
[0;37;40m▄▓█▓┌─ ███▓┐ ▄██▓┌─ ███▓│ ███▓│ ███▓┌─ ███▓┐    ███▓┌──      ▄██▓┌─ ███▓│    ███▓┌── ███▓│  ███▓│ ███▓│░░░░░░░ ▄▓█▓┌─ ███▓┐      ▄██▓┌─ ███▓│ ███▓┌─ ███▓│ ███▓┌─ ███▓┐ ███▓┌─ ███▓┐ ███▓┌─ ███▓│ ███▓│  ███▓│[0m
[0;37;40m███▓│  ████│ ▀███▄▄▄▄▄ ─┘ ███▓│ ███▓│  ████│ ░░ ███▓│░░      ▀███▄▄▄▄▄ ─┘ ░░ ███▓│░░ ▀███▄▄▄████│ ███▓│▒▒▒▒▒▒▒ ███▓│  ████│      ▀███▄▄▄▄▄ ─┘ ████▄▄  ───┘ ███▓│▄▄████│ ████▄▄▄██▀┌┘ ███▓│░  ───┘ ████▄▄▄████│[0m
[0;37;40m███▓│  ███▓│ ▄▄▄▄┌─ ███▓│ ███▓│ ███▓│  ███▓│ ▒▒ ███▓│▒▒      ▄▄▄▄┌─ ███▓│ ▒▒ ███▓│▒▒ ▄▄▄▄┌─ ███▓│ ███▓│▓ ▄▄▄▄  ███▓│  ███▓│      ▄▄▄▄┌─ ███▓│ ███▓┌─┘▄▄▄▄  ███▓├─ ████│ ███▓┌─ ███▄┐ ███▓│▒ ▄▄▄▄  ███▓┌─ ████│[0m
[0;37;40m└▓██▄▄▄█▓┌─┘ ▓███▄▄▄██▓┌┘ ███▓│ ▓███│  ███▓│ ▀▀ ███▓│▀▀      ▓███▄▄▄██▓┌┘ ▀▀ ███▓│▀▀ ▓███▄▄▄██▓┌┘ ▀███▄▄▄███▓│ └▓██▄▄▄█▓┌─┘      ▓███▄▄▄██▓┌┘ ▀███▄▄▄███▓│ ▓██▓│  ▓██▓│ ▓███│  ███▓│ ▀███▄▄▄███▓│ ▓██▓│  ▓██▓│[0m
[0;37;40m  ───────┘    ─────────┘   ───┘  ───┘   ───┘     ───┘         ─────────┘      ───┘    ─────────┘     ────────┘   ───────┘         ─────────┘     ────────┘  ───┘   ───┘  ───┘   ───┘    ────────┘  ───┘   ───┘[0m
OSINT Stylometric Search Suite
Version: 0.2.1
Last updated: 08/2026
Author: Laurent Schueller, https://sublysis.github.io
License: European Union Public Licence (EUPL) v1.2
For authorized penetration testing and network auditing use only. All rights reserved.
Manual: github.com/sublysis/osint_stylometric_search
'''


def main(argv=None):

    print(ascii_header)

    parser = argparse.ArgumentParser(
        prog="osint",
        description="Classify artifacts from a txt list, fetch texts and analyze them via NLP.",
    )
    parser.add_argument("input", nargs="?", help="txt file with artifacts (one per line); not needed with --from-json")
    parser.add_argument(
        "--from-json", metavar="FILE",
        help="regenerate --report/--json output from a previously written --json file, with no network calls "
             "(skips --fetch/--whois/--certs/--search/--correlate/--monitor/--save/--history, if given)",
    )
    parser.add_argument("--fetch", action="store_true", help="fetch text from URL artifacts")
    parser.add_argument("--whois", action="store_true", help="RDAP WHOIS lookup for URL artifacts (registrar/registrant/dates)")
    parser.add_argument("--certs", action="store_true", help="Certificate Transparency lookup via crt.sh (subdomains, cert IDs)")
    parser.add_argument("--nlp", action="store_true", help="NER, keyphrases, stylometry on fetched texts (implies --fetch)")
    parser.add_argument(
        "--case-dir", metavar="DIR",
        help="directory containing uploads/ for `file:` artifacts (default: input file's directory)",
    )
    parser.add_argument("--search", action="store_true", help="search the web for selectors via search provider + OSINT tools (maigret/holehe)")
    parser.add_argument("--provider", metavar="NAME", help="search provider override (searxng|brave|serpapi)")
    parser.add_argument("--limit", type=int, default=10, help="max web hits per selector (default 10)")
    parser.add_argument("--correlate", action="store_true", help="correlate hits: shared sources/entities/style/registrant -> links")
    parser.add_argument("--monitor", action="store_true", help="compare with the previous run of the same input (new/gone targets & links)")
    parser.add_argument("--history", action="store_true", help="list stored runs for this input and exit")
    parser.add_argument("--save", action="store_true", help="save run to SQLite (config.report.db_path)")
    parser.add_argument(
        "--report", nargs="?", const="md,html", metavar="FORMATS",
        help="generate report files (md,html,graphml,maltego; default md,html)",
    )
    parser.add_argument("--out-dir", metavar="DIR", help="target directory for reports")
    parser.add_argument("--json", metavar="FILE", help="write results as JSON")
    parser.add_argument("--config", metavar="FILE", help="additional config file (overrides default.yaml)")
    args = parser.parse_args(argv)

    if not args.from_json and not args.input:
        parser.error("input is required unless --from-json is given")

    try:
        config = load_config(args.config)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.from_json:
        return _run_from_json(args, config)

    if args.history:
        from osint.monitor import run_timeline

        _print_timeline(run_timeline(config, args.input))
        return 0

    try:
        artifacts = parse_file(args.input, config)
    except FileNotFoundError:
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1

    groups = group_by_type(artifacts)
    _print_summary(groups)

    results = [{"type": a.type.value, "value": a.value, "raw": a.raw} for a in artifacts]
    output = {"artifacts": results}

    if args.fetch or args.nlp:
        case_dir = args.case_dir or os.path.dirname(os.path.abspath(args.input)) or "."
        _fetch_urls(groups.get(ArtifactType.URL, []), config, results)
        _load_local_files(groups.get(ArtifactType.FILE, []), case_dir, config, results)

    if args.whois:
        _run_whois(groups.get(ArtifactType.URL, []), config, results)

    if args.certs:
        _run_certs(groups.get(ArtifactType.URL, []), config, results)

    if args.nlp:
        stylometry = _run_nlp(results, config)
        if stylometry is not None:
            output["stylometry"] = stylometry

    if args.search:
        _run_search(groups, config, results, args.provider, args.limit)

    if args.correlate:
        from osint.correlate import correlate

        result = correlate(results, output.get("stylometry"), config)
        output["correlation"] = result.to_dict()
        _print_correlation(result)

    if args.monitor:
        from osint.monitor import compare_to_previous

        diff = compare_to_previous(config, output, args.input)
        if diff is None:
            print("\n[monitor] no previous run found for this input.")
        else:
            output["monitor"] = diff
            _print_monitor(diff)

    run_id = None
    if args.save:
        from osint.report import save_run

        run_id, db_path = save_run(output, args.input, config)
        print(f"\n[report] run #{run_id} saved -> {db_path}")

    if args.report:
        from osint.report import generate

        formats = [f.strip() for f in args.report.split(",") if f.strip()]
        written = generate(output, config, args.input, formats, run_id, args.out_dir)
        for fmt, path in written.items():
            print(f"[report] {fmt} -> {path}")

    if args.json:
        _write_json(args.json, output)

    return 0


_REPLAY_SKIPPED_FLAGS = (
    "fetch", "whois", "certs", "nlp", "search", "correlate", "monitor", "save", "history",
)


def _run_from_json(args, config):
    ignored = [f"--{name}" for name in _REPLAY_SKIPPED_FLAGS if getattr(args, name)]
    if ignored:
        print(f"[replay] ignoring {', '.join(ignored)} - --from-json only regenerates reports, no network calls")

    try:
        with open(args.from_json, encoding="utf-8") as f:
            output = json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {args.from_json}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {args.from_json}: {e}", file=sys.stderr)
        return 1

    print(f"\n[replay] loaded {len(output.get('artifacts', []))} artifact(s) from {args.from_json}")

    if args.report:
        from osint.report import generate

        formats = [f.strip() for f in args.report.split(",") if f.strip()]
        written = generate(output, config, args.from_json, formats, None, args.out_dir)
        for fmt, path in written.items():
            print(f"[report] {fmt} -> {path}")
    else:
        print("[replay] nothing to do - pass --report to generate report files")

    if args.json:
        _write_json(args.json, output)

    return 0


def _write_json(path, output):
    json_dir = os.path.dirname(path)
    if json_dir:
        os.makedirs(json_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nWritten: {path}")


def _print_summary(groups):
    total = sum(len(v) for v in groups.values())
    print(f"{total} artifact(s) detected:")
    for t in ArtifactType:
        items = groups.get(t)
        if items:
            print(f"  {t.value:9} {len(items):>4}")


def _fetch_urls(url_artifacts, config, results):
    if not url_artifacts:
        return
    print(f"\nFetching {len(url_artifacts)} URL(s) ...")
    for outcome in pipeline.fetch_urls(url_artifacts, config, results):
        if outcome["ok"]:
            print(f"  [ok {outcome['status']}] {outcome['value']} ({outcome['chars']} characters)")
        else:
            print(f"  [--] {outcome['value']} -> {outcome['error']}")


def _load_local_files(file_artifacts, case_dir, config, results):
    if not file_artifacts:
        return
    print(f"\nLoading {len(file_artifacts)} local file(s) from {case_dir}/uploads ...")
    for outcome in pipeline.load_local_files(file_artifacts, case_dir, config, results):
        if outcome["ok"]:
            print(f"  [ok] {outcome['value']} ({outcome['chars']} characters)")
        else:
            print(f"  [--] {outcome['value']} -> {outcome['error']}")


def _run_whois(url_artifacts, config, results):
    if not url_artifacts:
        return
    from osint.correlate.normalize import canonical_domain
    from osint.whois import WhoisClient

    print(f"\n[whois] RDAP lookup for {len(url_artifacts)} URL(s) ...")
    client = WhoisClient(config)
    by_value = {r["value"]: r for r in results}
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
            print(f"  {art.value} -> {domain}: registrar={result.registrar or '?'}{note}")
        else:
            print(f"  {art.value} -> {domain}: {result.error}")


def _run_certs(url_artifacts, config, results):
    if not url_artifacts:
        return
    from osint.certs import CertClient
    from osint.correlate.normalize import canonical_domain

    print(f"\n[certs] Certificate Transparency lookup for {len(url_artifacts)} URL(s) ...")
    client = CertClient(config)
    by_value = {r["value"]: r for r in results}
    for art in url_artifacts:
        domain = canonical_domain(art.value)
        result = client.lookup(domain)
        entry = by_value.get(art.value, {})
        entry["certs"] = result.to_dict()
        if result.ok:
            print(f"  {art.value} -> {domain}: {result.cert_count} cert(s), {len(result.subdomains)} subdomain(s)")
        else:
            print(f"  {art.value} -> {domain}: {result.error}")


def _run_nlp(results, config):
    docs = [r for r in results if r.get("text")]
    if not docs:
        print("\n[nlp] no texts available.")
        return None
    print(f"\n[nlp] analyzing {len(docs)} text(s) ...")
    _nlp_entities_keyphrases(docs, config)
    return _nlp_stylometry(docs, config)


def _nlp_entities_keyphrases(docs, config):
    from osint.nlp import EntityExtractor, KeyphraseExtractor, extract_regex_entities

    cfg = config.get("nlp", {})
    ner = EntityExtractor(cfg.get("spacy_model", "de_core_news_lg"))
    kp = KeyphraseExtractor(lang=cfg.get("keyphrase_lang", "de"), top=cfg.get("keyphrase_top", 20))
    ner_ok, kp_ok = True, True

    for d in docs:
        text = d["text"]
        try:
            ents = ner.extract(text, use_spacy=ner_ok)
        except RuntimeError as e:
            print(f"  [nlp] NER (spaCy) skipped: {e}")
            ner_ok = False
            ents = extract_regex_entities(text)
        d["entities"] = [{"label": e.label, "text": e.text} for e in ents]

        if kp_ok:
            try:
                d["keyphrases"] = [{"text": k.text, "score": round(k.score, 4)} for k in kp.extract(text)]
            except RuntimeError as e:
                print(f"  [nlp] keyphrases (yake) skipped: {e}")
                kp_ok = False

        print(f"  {d['value']}: {len(d.get('entities', []))} Entities, {len(d.get('keyphrases', []))} Keyphrases")


def _nlp_stylometry(docs, config):
    from osint.nlp import StylometryModel, basic_features

    for d in docs:
        d["style"] = {k: round(v, 5) for k, v in basic_features(d["text"]).items()}

    if len(docs) < 2:
        print("  [nlp] stylometry comparison needs >=2 texts.")
        return []

    labels = [d["value"] for d in docs]
    threshold = config.get("nlp", {}).get("stylometry_threshold", 0.0)
    try:
        model = StylometryModel().fit([d["text"] for d in docs], labels)
    except RuntimeError as e:
        print(f"  [nlp] stylometry (sklearn) skipped: {e}")
        return None

    pairs = model.most_similar_pairs(threshold=threshold)
    print("  Stylometric similarity (author fingerprint):")
    for a, b, score in pairs[:10]:
        print(f"    {score:.3f}  {a}  <->  {b}")
    return [{"a": a, "b": b, "similarity": round(score, 4)} for a, b, score in pairs]


def _run_search(groups, config, results, provider_name, limit):
    from osint.search import SearchError, get_provider
    from osint.search.tools import HoleheWrapper, MaigretWrapper

    by_value = {r["value"]: r for r in results}

    try:
        provider = get_provider(config, provider_name)
    except SearchError as e:
        print(f"\n[search] {e}")
        provider = None

    queries = []
    for art_type, fmt in ((ArtifactType.NAME, '"{}"'), (ArtifactType.EMAIL, '"{}"'), (ArtifactType.USERNAME, "{}")):
        for a in groups.get(art_type, []):
            queries.append((a.value, fmt.format(a.value)))

    if provider is not None and queries:
        print(f"\n[search] web search via '{provider.name}' for {len(queries)} selector(s) ...")
        for value, query in queries:
            try:
                hits = provider.search(query, limit=limit)
            except SearchError as e:
                print(f"  [search] provider skipped: {e}")
                break
            entry = by_value.get(value, {})
            entry.setdefault("search", []).extend(h.to_dict() for h in hits)
            print(f"  {value}: {len(hits)} web hit(s)")

    _run_tool(MaigretWrapper(), groups.get(ArtifactType.USERNAME, []), by_value)
    _run_tool(HoleheWrapper(), groups.get(ArtifactType.EMAIL, []), by_value)


def _print_timeline(runs):
    if not runs:
        print("No stored runs for this input.")
        return
    print(f"{len(runs)} stored run(s):")
    print(f"  {'ID':>4}  {'Timestamp':<20} {'Artifacts':>9} {'Targets':>6} {'Links':>6}")
    for r in runs:
        print(f"  {r['id']:>4}  {r['created_at']:<20} {r['artifacts']:>9} {r['targets']:>6} {r['links']:>6}")


def _print_monitor(diff):
    print(f"\n[monitor] comparison with run #{diff.get('previous_run_id')}:")
    print(f"  +{len(diff.get('new_targets', []))} new targets, -{len(diff.get('gone_targets', []))} gone")
    for t in diff.get("new_targets", [])[:10]:
        print(f"    + {t['value']}")
    print(f"  +{len(diff.get('new_links', []))} new links, -{len(diff.get('gone_links', []))} gone")
    for l in diff.get("new_links", [])[:10]:
        print(f"    + {l['score']:.2f}  {l['a']} <-> {l['b']}")


def _print_correlation(result):
    shared = [t for t in result.targets if t.seed_count >= 2]
    print(
        f"\n[correlate] {len(result.targets)} target(s), "
        f"{len(shared)} shared by >=2 selectors, {len(result.links)} link(s)"
    )
    for t in shared[:10]:
        print(f"  [{t.seed_count} seeds] {t.value}")
    for link in result.links[:10]:
        kinds = ", ".join(e.kind for e in link.evidence)
        print(f"  {link.score:.2f}  {link.a} <-> {link.b}  ({kinds})")


def _run_tool(tool, artifacts, by_value):
    if not artifacts:
        return
    if not tool.available():
        print(f"[search] {tool.binary} not installed - {len(artifacts)} target(s) skipped")
        return
    print(f"[search] {tool.name} for {len(artifacts)} target(s) ...")
    for a in artifacts:
        res = tool.run(a.value)
        entry = by_value.get(a.value, {})
        entry.setdefault("accounts", []).extend(res.hits)
        if res.error:
            print(f"  {a.value}: error - {res.error}")
        else:
            print(f"  {a.value}: {len(res.hits)} account/hit(s)")


if __name__ == "__main__":
    raise SystemExit(main())
