import argparse
import json
import sys

from osint.config import load_config
from osint.fetcher import Fetcher
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
Vallanx OSINT Stylometric Search Suite
www.vallanx.com
Version: 0.1.0
Manual: github.com/vallanx-team/osint_stylometric_search
Last updated: 07/2026 | Author: aristopunk | Copyright: Vallanx | For authorized penetration testing and network auditing use only. All rights reserved.
'''


def main(argv=None):

    print(ascii_header)

    parser = argparse.ArgumentParser(
        prog="osint",
        description="Artefakte aus einer txt-Liste klassifizieren, Texte holen und per NLP analysieren.",
    )
    parser.add_argument("input", help="txt-Datei mit Artefakten (eine pro Zeile)")
    parser.add_argument("--fetch", action="store_true", help="Text von URL-Artefakten abrufen")
    parser.add_argument("--nlp", action="store_true", help="NER, Keyphrases, Stilometrie auf geholten Texten (impliziert --fetch)")
    parser.add_argument("--search", action="store_true", help="Selektoren via Suchprovider + OSINT-Tools (maigret/holehe) im Netz suchen")
    parser.add_argument("--provider", metavar="NAME", help="Suchprovider override (searxng|brave|serpapi)")
    parser.add_argument("--limit", type=int, default=10, help="max Web-Treffer pro Selektor (default 10)")
    parser.add_argument("--correlate", action="store_true", help="Treffer korrelieren: geteilte Quellen/Entitaeten/Stil -> Verknuepfungen")
    parser.add_argument("--monitor", action="store_true", help="mit vorherigem Run derselben Eingabe vergleichen (neue/verschwundene Ziele & Verknuepfungen)")
    parser.add_argument("--history", action="store_true", help="gespeicherte Runs dieser Eingabe auflisten und beenden")
    parser.add_argument("--save", action="store_true", help="Run in SQLite speichern (config.report.db_path)")
    parser.add_argument("--report", nargs="?", const="md,html", metavar="FORMATS", help="Report-Dateien erzeugen (md,html; default md,html)")
    parser.add_argument("--out-dir", metavar="DIR", help="Zielverzeichnis fuer Reports")
    parser.add_argument("--json", metavar="FILE", help="Ergebnisse als JSON schreiben")
    parser.add_argument("--config", metavar="FILE", help="zusaetzliche Config-Datei (ueberschreibt default.yaml)")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except RuntimeError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1

    if args.history:
        from osint.monitor import run_timeline

        _print_timeline(run_timeline(config, args.input))
        return 0

    try:
        artifacts = parse_file(args.input, config)
    except FileNotFoundError:
        print(f"Fehler: Datei nicht gefunden: {args.input}", file=sys.stderr)
        return 1

    groups = group_by_type(artifacts)
    _print_summary(groups)

    results = [{"type": a.type.value, "value": a.value, "raw": a.raw} for a in artifacts]
    output = {"artifacts": results}

    if args.fetch or args.nlp:
        _fetch_urls(groups.get(ArtifactType.URL, []), config, results)

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
            print("\n[monitor] kein frueherer Run fuer diese Eingabe gefunden.")
        else:
            output["monitor"] = diff
            _print_monitor(diff)

    run_id = None
    if args.save:
        from osint.report import save_run

        run_id, db_path = save_run(output, args.input, config)
        print(f"\n[report] Run #{run_id} gespeichert -> {db_path}")

    if args.report:
        from osint.report import generate

        formats = [f.strip() for f in args.report.split(",") if f.strip()]
        written = generate(output, config, args.input, formats, run_id, args.out_dir)
        for fmt, path in written.items():
            print(f"[report] {fmt} -> {path}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\nGeschrieben: {args.json}")

    return 0


def _print_summary(groups):
    total = sum(len(v) for v in groups.values())
    print(f"{total} Artefakt(e) erkannt:")
    for t in ArtifactType:
        items = groups.get(t)
        if items:
            print(f"  {t.value:9} {len(items):>4}")


def _fetch_urls(url_artifacts, config, results):
    if not url_artifacts:
        return
    print(f"\nRufe {len(url_artifacts)} URL(s) ab ...")
    fetcher = Fetcher(config)
    by_value = {r["value"]: r for r in results}
    for art in url_artifacts:
        res = fetcher.fetch(art.value)
        entry = by_value.get(art.value, {})
        if res.ok and res.text:
            entry["title"] = res.title
            entry["text"] = res.text
            entry["chars"] = len(res.text)
            print(f"  [ok {res.status}] {art.value} ({len(res.text)} Zeichen)")
        else:
            entry["error"] = res.error or f"HTTP {res.status}"
            print(f"  [--] {art.value} -> {entry['error']}")


def _run_nlp(results, config):
    docs = [r for r in results if r.get("text")]
    if not docs:
        print("\n[nlp] keine Texte vorhanden.")
        return None
    print(f"\n[nlp] analysiere {len(docs)} Text(e) ...")
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
            print(f"  [nlp] NER (spaCy) uebersprungen: {e}")
            ner_ok = False
            ents = extract_regex_entities(text)
        d["entities"] = [{"label": e.label, "text": e.text} for e in ents]

        if kp_ok:
            try:
                d["keyphrases"] = [{"text": k.text, "score": round(k.score, 4)} for k in kp.extract(text)]
            except RuntimeError as e:
                print(f"  [nlp] Keyphrases (yake) uebersprungen: {e}")
                kp_ok = False

        print(f"  {d['value']}: {len(d.get('entities', []))} Entities, {len(d.get('keyphrases', []))} Keyphrases")


def _nlp_stylometry(docs, config):
    from osint.nlp import StylometryModel, basic_features

    for d in docs:
        d["style"] = {k: round(v, 5) for k, v in basic_features(d["text"]).items()}

    if len(docs) < 2:
        print("  [nlp] Stilometrie-Vergleich braucht >=2 Texte.")
        return []

    labels = [d["value"] for d in docs]
    threshold = config.get("nlp", {}).get("stylometry_threshold", 0.0)
    try:
        model = StylometryModel().fit([d["text"] for d in docs], labels)
    except RuntimeError as e:
        print(f"  [nlp] Stilometrie (sklearn) uebersprungen: {e}")
        return None

    pairs = model.most_similar_pairs(threshold=threshold)
    print("  Stilometrie-Aehnlichkeit (Autor-Fingerabdruck):")
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
        print(f"\n[search] Websuche via '{provider.name}' fuer {len(queries)} Selektor(en) ...")
        for value, query in queries:
            try:
                hits = provider.search(query, limit=limit)
            except SearchError as e:
                print(f"  [search] Provider uebersprungen: {e}")
                break
            entry = by_value.get(value, {})
            entry.setdefault("search", []).extend(h.to_dict() for h in hits)
            print(f"  {value}: {len(hits)} Web-Treffer")

    _run_tool(MaigretWrapper(), groups.get(ArtifactType.USERNAME, []), by_value)
    _run_tool(HoleheWrapper(), groups.get(ArtifactType.EMAIL, []), by_value)


def _print_timeline(runs):
    if not runs:
        print("Keine gespeicherten Runs fuer diese Eingabe.")
        return
    print(f"{len(runs)} gespeicherte(r) Run(s):")
    print(f"  {'ID':>4}  {'Zeitpunkt':<20} {'Artefakte':>9} {'Ziele':>6} {'Links':>6}")
    for r in runs:
        print(f"  {r['id']:>4}  {r['created_at']:<20} {r['artifacts']:>9} {r['targets']:>6} {r['links']:>6}")


def _print_monitor(diff):
    print(f"\n[monitor] Vergleich mit Run #{diff.get('previous_run_id')}:")
    print(f"  +{len(diff.get('new_targets', []))} neue Ziele, -{len(diff.get('gone_targets', []))} entfallen")
    for t in diff.get("new_targets", [])[:10]:
        print(f"    + {t['value']}")
    print(f"  +{len(diff.get('new_links', []))} neue Verknuepfungen, -{len(diff.get('gone_links', []))} entfallen")
    for l in diff.get("new_links", [])[:10]:
        print(f"    + {l['score']:.2f}  {l['a']} <-> {l['b']}")


def _print_correlation(result):
    shared = [t for t in result.targets if t.seed_count >= 2]
    print(
        f"\n[correlate] {len(result.targets)} Ziel(e), "
        f"{len(shared)} von >=2 Selektoren geteilt, {len(result.links)} Verknuepfung(en)"
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
        print(f"[search] {tool.binary} nicht installiert - {len(artifacts)} Ziel(e) uebersprungen")
        return
    print(f"[search] {tool.name} fuer {len(artifacts)} Ziel(e) ...")
    for a in artifacts:
        res = tool.run(a.value)
        entry = by_value.get(a.value, {})
        entry.setdefault("accounts", []).extend(res.hits)
        if res.error:
            print(f"  {a.value}: Fehler - {res.error}")
        else:
            print(f"  {a.value}: {len(res.hits)} Konto/Treffer")


if __name__ == "__main__":
    raise SystemExit(main())
