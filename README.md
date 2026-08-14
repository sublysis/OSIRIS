# osint_stylometric_search

OSINT-Tool: klassifiziert Artefakte (URL, E-Mail, Username, Name) aus einer
txt-Liste, holt Texte von URLs und korreliert Urheber/Muster im Netz.

Trotz Name ist **Sentiment nicht der Motor** — der Kern sind **Selektor-Suche**
(harte Wiedererkennung) und **Stilometrie** (Schreibstil-Fingerabdruck).
Sentiment ist optionale Anreicherung.

## Pipeline (modular)

```
input_parser/  ->  fetcher/  ->  nlp/  ->  search/  ->  correlate/  ->  report/
```

Status: **komplette Pipeline lauffähig** (Modul 1-6). Volle NLP-/Such-Qualität
erst nach Installation der optionalen Deps (siehe Setup) bzw. mit laufendem
SearXNG und installierten OSINT-Tools.

## Setup (lokal / venv)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

NLP-Kern (NER/Keyphrases/Stilometrie): `pip install -r requirements-nlp.txt` und
`python -m spacy download de_core_news_lg`.
Optionales Sentiment (groß, torch): `pip install -r requirements-sentiment.txt`.

**Automatisch auf einem Debian/Ubuntu-Server (inkl. SearXNG):** `bash scripts/install.sh`
(siehe Deployment).

## Nutzung

```bash
# Nur klassifizieren:
python cli.py examples/artifacts.txt

# Texte von URLs holen:
python cli.py examples/artifacts.txt --fetch

# Voller Durchlauf: fetch + NLP + Websuche + Korrelation + Report + JSON:
python cli.py examples/artifacts.txt --nlp --search --correlate --save --report --json out.json
```

### Flags

| Flag | Wirkung |
|------|---------|
| `--fetch` | Text von URL-Artefakten abrufen (robots.txt + Rate-Limit) |
| `--nlp` | NER, Keyphrases, Stilometrie (impliziert `--fetch`) |
| `--search` | Selektoren via Suchprovider + maigret/holehe suchen |
| `--provider NAME` | Provider override: `searxng` (default), `brave`, `serpapi` |
| `--limit N` | max Web-Treffer pro Selektor |
| `--correlate` | geteilte Quellen/Entitaeten/Stil -> gescorte Verknuepfungen |
| `--monitor` | mit vorherigem Run vergleichen (neue/verschwundene Ziele & Links) |
| `--history` | gespeicherte Runs dieser Eingabe auflisten und beenden |
| `--save` | Run in SQLite persistieren (`config.report.db_path`) |
| `--report [md,html]` | lesbare Reports schreiben (`config.report.output_dir`) |
| `--out-dir DIR` | Zielverzeichnis fuer Reports |
| `--json FILE` | vollstaendiges Ergebnis als JSON |

Eingabeformat: eine Zeile pro Artefakt. Typ wird automatisch erkannt, lässt sich
aber per Präfix erzwingen (`name:`, `username:`, `url:`, `email:`).
`#`-Zeilen und Leerzeilen werden ignoriert.

## Artifact Types (English)

Each line in the input file is classified into one of these types. Detection
is automatic, but you can force a type with an explicit `type: value` prefix
(case-insensitive). Quotes around the value (`"..."` or `'...'`) are stripped.

| Type | Explicit prefix | Auto-detected when | Normalization | Used for |
|------|------------------|---------------------|----------------|----------|
| `url` | `url:` | starts with `http://`/`https://`, or looks like a bare domain (`example.com`, `example.org/blog`) | `https://` is prepended if no scheme given | `--fetch` downloads the page text (robots.txt + rate-limit respected); `--nlp` runs NER/keyphrases/stylometry on the fetched text |
| `email` | `email:` | matches `local@domain.tld` | lowercased | `--search` runs holehe (checks which services the address is registered on) and web search |
| `username` | `username:` | no spaces, not an email/URL/domain (also matches a leading `@handle`) | leading `@` stripped | `--search` runs maigret (checks the handle across social platforms) and web search |
| `name` | `name:` | contains a space and isn't classified as URL/email | left as-is | `--search` runs a web search (quoted exact-match query) |
| `unknown` | — | fallback type in the enum; not currently reachable, since `_detect()` always falls back to `username` for anything without a space | — | ignored by the pipeline |

Examples (see `examples/artifacts.txt`):

```
# comments and blank lines are ignored
https://example.com
example.org/blog
max.mustermann@example.com
@nightowl_88
nightowl_88
Max Mustermann
"Erika Fake-Name"
name: J. Doe
username: gh0st.writer
```

Only `url` gets its page content fetched. `email`, `username`, and `name` are
treated as **selectors** — they're looked up (web search + maigret/holehe),
not fetched as pages. `--correlate` then looks for shared sources, entities,
or writing style linking different selectors/URLs together.

## Example Workflow (English)

There is no crawler — you curate the artifact list yourself, one artifact per
line. `--fetch`/`--nlp` only pull the text of URLs you already listed; they
don't discover new links, emails, or usernames on the page.

1. Create an input file with the artifacts you want to investigate:

```bash
cat > targets.txt <<'EOF'
url:https://example.com
url:https://example.com/about
email:info@example.com
username:examplecorp
name:Jane Doe
EOF
```

2. Run the full pipeline: fetch page text, run NLP (NER/keyphrases/stylometry),
   search the selectors on the web + maigret/holehe, correlate shared
   sources/style, persist the run, and write reports:

```bash
python cli.py targets.txt --fetch --nlp --search --correlate --save --report --json out.json
```

3. Re-run later against the same file to see what changed:

```bash
python cli.py targets.txt --nlp --search --correlate --monitor --save
```

4. Inspect all stored runs for this input file:

```bash
python cli.py targets.txt --history
```

If you want automatic artifact discovery (e.g. crawling `example.com` for
sitemap links, emails, or social handles), that's a separate feature — not
part of `cli.py` today.

## Konfiguration

`config/default.yaml` steuert Fetcher (User-Agent, Rate-Limit, robots.txt),
Suchprovider und Report. API-Keys gehören in `config/secrets.yaml` (gitignored).
Standardquelle für Websuche ist **selbst gehostetes SearXNG**; Bezahl-APIs
(Brave, SerpAPI) sind optional zuschaltbar.

### Fetcher / robots.txt

`--fetch` respektiert standardmäßig `robots.txt` (`fetcher.respect_robots: true`).
Verbietet die Zielseite den Zugriff für den konfigurierten User-Agent, wird das
URL-Artefakt übersprungen (`durch robots.txt verboten`) statt trotzdem geholt zu
werden — bewusste Design-Entscheidung für verantwortungsvolles/legales
Scraping, siehe auch Abschnitt „Rechtlich".

- **Fail-open bei nicht erreichbarer robots.txt**: Ist die Datei selbst nicht
  abrufbar (Timeout, 404, DNS-Fehler etc.), wird das Fetchen erlaubt. Nur ein
  *explizites* Disallow blockiert.
- **Rate-Limit**: `fetcher.min_delay_per_domain` (Default 2s) erzwingt eine
  Mindestpause zwischen Requests an dieselbe Domain.
- **User-Agent**: `fetcher.user_agent` identifiziert das Tool gegenüber dem
  Zielserver (Default `osint-tool/0.1 (+research; contact via config)`).
- **Abschalten**: `respect_robots: false` in `config/default.yaml` (oder in
  einer per `--config` übergebenen Override-Datei) deaktiviert die Prüfung
  komplett. Nur nach Rücksprache/rechtlicher Prüfung verwenden.

## Monitoring / Zeitreihen

`--save` legt jeden Lauf in SQLite ab. `--monitor` vergleicht den aktuellen Lauf
mit dem letzten gespeicherten Lauf **derselben Eingabedatei** und zeigt neue bzw.
verschwundene Ziele und Verknüpfungen. `--history` listet die bisherigen Läufe.

```bash
# Erstlauf speichern:
python cli.py artefakte.txt --nlp --search --correlate --save

# Spaeter erneut - was ist neu?
python cli.py artefakte.txt --nlp --search --correlate --monitor --save

# Verlauf ansehen:
python cli.py artefakte.txt --history
```

## Interpreting Scores

The `--correlate` link score (e.g. `0.80`) and the `--nlp` stylometric
similarity score are **not** statistical measures like a correlation
coefficient or standard deviation — they're a heuristic weighted evidence
tally and a cosine-similarity metric, respectively. See
[`docs/interpreting-scores.md`](docs/interpreting-scores.md) for a full
explanation and a checklist for reading results responsibly before drawing
conclusions.

## Deployment (Vultr VPS)

Auf einem frischen Debian/Ubuntu-Server:

```bash
git clone <repo> && cd osint_stylometric_search
bash scripts/install.sh            # Deps + spaCy-Modell + maigret/holehe + SearXNG (Docker)
# optional: --with-sentiment (torch), --no-searxng, --no-tools, --port N
```

Das Script legt ein `.venv/` an, installiert alles und startet **SearXNG** als
Docker-Container, gebunden an `127.0.0.1:8080` (nicht öffentlich erreichbar), mit
aktivierter JSON-API und deaktiviertem Rate-Limiter. Danach:

```bash
source .venv/bin/activate
python cli.py deine_artefakte.txt --nlp --search --correlate --save --report
```

Sicherheit: SearXNG bleibt lokal (nur der VPS selbst greift zu). Der generierte
`server.secret_key` liegt in `searxng/settings.yml` (gitignored).

## Rechtlich

EU/DSGVO beachten, sobald reale Personen profiliert/korreliert werden:
Zweckbindung, Datensparsamkeit, Nachvollziehbarkeit. Nur für legitime Zwecke
(autorisiertes Security-Research, Journalismus, Marken-/Threat-Monitoring).
