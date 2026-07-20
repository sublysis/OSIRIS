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

## Konfiguration

`config/default.yaml` steuert Fetcher (User-Agent, Rate-Limit, robots.txt),
Suchprovider und Report. API-Keys gehören in `config/secrets.yaml` (gitignored).
Standardquelle für Websuche ist **selbst gehostetes SearXNG**; Bezahl-APIs
(Brave, SerpAPI) sind optional zuschaltbar.

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
