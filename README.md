![[banner.webp]]

<p align="center">
  <img alt="banner.webp" src="https://github.com/sublysis/OSIRIS/blob/7cbe086e5e6ee26f4cf5c7c4deb729b4f633d636/banner.webp?raw=true" data-hpc="true" containertiming="hpc" style="max-width:100%">
</p>

# OSIRIS - Open Source Intelligence Research & Investigative Stylometry

> *Last updated: 10/2026 | Author: Laurent Schueller | For authorized penetration testing, lab / training, and auditing use only.*

##### OSINT Stylometric Search with modular components and ML

OSINT Stylometric Search classifies artifacts (URL, email, username, name) from a txt list, fetches text from URLs, and correlates authorship/patterns across the web. The core is **selector search** (hard re-identification) and **stylometry** (writing-style fingerprint). Sentiment is optional enrichment.

## Use Cases

- Research
- Security Auditing
- Investigative Journalism
- OSINT work

## Pipeline (modular)

```
input_parser/  ->  fetcher/  ->  nlp/  ->  search/  ->  whois/  ->  certs/  ->  correlate/  ->  report/
```

Status: **full pipeline runnable**, including the optional WHOIS/RDAP and Certificate Transparency stages. Full NLP/search quality only after installing the optional deps (see Setup) resp. with a running SearXNG and installed OSINT tools.

## Setup (local / venv)

```bash
python -m venv .venv
.venv\Scripts\activate # Win
pip install -r requirements.txt
```

NLP core (NER/keyphrases/stylometry): `pip install -r requirements-nlp.txt` and `python -m spacy download <model>`, where `<model>` matches `nlp.spacy_model` in `config/default.yaml` (default `en_core_web_md`; see the [spaCy models list](https://github.com/explosion/spacy-models) for alternatives, e.g. `de_core_news_lg` for German). Changing `nlp.spacy_model` in the config does **not** install/download the model. It must be pulled separately in every environment that runs `--nlp` (`scripts/install.sh`
handles this automatically, see Deployment).

Optional sentiment (large, torch): `pip install -r requirements-sentiment.txt`. `--whois` and `--certs` need no extra dependency (both use `requests`, already a core requirement). Favicon hashing (part of `--fetch`) uses `mmh3` (Shodan-compatible hash) if installed, also in core requirements, but falls back to md5-only hashing if it's missing.

**Automatic on a Debian/Ubuntu server (incl. SearXNG):** `bash scripts/install.sh` (see Deployment).

## Usage

```bash
# Classify only:
python cli.py examples/artifacts.txt

# Fetch text from URLs:
python cli.py examples/artifacts.txt --fetch

# Full run: fetch + NLP + web search + WHOIS + certs + correlation + report + JSON:
python cli.py examples/artifacts.txt --nlp --search --whois --certs --correlate --save --report --json out.json
```

### Flags

| Flag | Effect |
|------|--------|
| `--fetch` | fetch text from URL artifacts (robots.txt + rate limit); also hashes the page favicon |
| `--whois` | RDAP WHOIS lookup for URL artifacts (registrar/registrant/dates) |
| `--certs` | Certificate Transparency lookup via crt.sh (subdomains, certificate IDs) |
| `--nlp` | NER, keyphrases, stylometry (implies `--fetch`) |
| `--search` | look up selectors via search provider + maigret/holehe |
| `--provider NAME` | provider override: `searxng` (default), `brave`, `serpapi` |
| `--limit N` | max web hits per selector |
| `--correlate` | shared sources/entities/style/registrant/favicon/cert -> scored links |
| `--monitor` | compare with the previous run (new/gone targets & links) |
| `--history` | list stored runs for this input and exit |
| `--save` | persist run to SQLite (`config.report.db_path`) |
| `--report [md,html,graphml,maltego]` | write reports; `graphml`/`maltego` export the `--correlate` link network as a graph (not part of the default `md,html`) |
| `--out-dir DIR` | target directory for reports |
| `--json FILE` | full result as JSON |
| `--from-json FILE` | regenerate `--report`/`--json` from a previously written `--json` file, no network calls (see below); replaces `input`, skips all other pipeline flags |

Input format: one artifact per line. Type is auto-detected, but can be forced with a prefix (`name:`, `username:`, `url:`, `email:`). `#` lines and blank lines are ignored.

## Artifact Types

Each line in the input file is classified into one of these types. Detection is automatic, but you can force a type with an explicit `type: value` prefix (case-insensitive). Quotes around the value (`"..."` or `'...'`) are stripped.

| Type       | Explicit prefix | Auto-detected when                                                                                                                 | Normalization                              | Used for                                                                                                                                                                                                                                                                        |
| ---------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `url`      | `url:`          | starts with `http://`/`https://`, or looks like a bare domain (`example.com`, `example.org/blog`)                                  | `https://` is prepended if no scheme given | `--fetch` downloads the page text and hashes its favicon (robots.txt + rate-limit respected); `--whois` looks up the domain's RDAP registrar/registrant/dates; `--certs` looks up crt.sh subdomains/certificate IDs; `--nlp` runs NER/keyphrases/stylometry on the fetched text |
| `email`    | `email:`        | matches `local@domain.tld`                                                                                                         | lowercased                                 | `--search` runs holehe (checks which services the address is registered on) and web search                                                                                                                                                                                      |
| `username` | `username:`     | no spaces, not an email/URL/domain (also matches a leading `@handle`)                                                              | leading `@` stripped                       | `--search` runs maigret (checks the handle across social platforms) and web search                                                                                                                                                                                              |
| `name`     | `name:`         | contains a space and isn't classified as URL/email                                                                                 | left as-is                                 | `--search` runs a web search (quoted exact-match query)                                                                                                                                                                                                                         |
| `file`     | `file:`         | never auto-detected (prefix-only); a bare filename is ambiguous against the domain/username heuristics                             | none (relative path kept as-is)            | a local document (uploaded into a case's `uploads/` directory) whose text is extracted by the `localfiles` stage - run via `cli.py --fetch` (`--case-dir` points at the `uploads/` parent) or incrementally via the MCP session layer; see ["MCP / Agentic Session Use"](#mcp--agentic-session-use)                                                                 |
| `unknown`  | --              | fallback type in the enum; not currently reachable, since `_detect()` always falls back to `username` for anything without a space | --                                         | ignored by the pipeline                                                                                                                                                                                                                                                         |

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

Only `url` gets its page content fetched (and optionally WHOIS-/certs-looked-up). `email`, `username`, and `name` are treated as **selectors**, they're looked up (web search + maigret/holehe), not fetched as pages. `--correlate` then looks for shared sources, entities, registrants, favicons, certificates, or writing style linking different selectors/URLs together.

## Example Workflow

There is no crawler, you curate the artifact list yourself, one artifact per line. `--fetch`/`--nlp`/`--whois`/`--certs` only work on artifacts you already listed; they don't discover new links, emails, or usernames on the page (though `--certs` does surface subdomains from CT logs as *data*, not
as new artifacts to further process).

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

2. Run the full pipeline: fetch page text + favicon, look up WHOIS and Certificate Transparency data, run NLP (NER/keyphrases/stylometry), search the selectors on the web + maigret/holehe, correlate shared sources/style/registrants/favicons/certs, persist the run, and write reports (including a graph export for Gephi/Maltego):

```bash
python cli.py targets.txt --fetch --whois --certs --nlp --search --correlate --save --report md,html,graphml --json out.json
```

3. Re-run later against the same file to see what changed:

```bash
python cli.py targets.txt --nlp --search --correlate --monitor --save
```

4. Inspect all stored runs for this input file:

```bash
python cli.py targets.txt --history
```

If you want automatic artifact discovery (e.g. crawling `example.com` for sitemap links, emails, or social handles), that's a separate feature, not part of `cli.py` today.

## Configuration

`config/default.yaml` controls the fetcher (user agent, rate limit, robots.txt, favicon hashing), WHOIS (RDAP endpoint, timeout, delay), Certificate Transparency (crt.sh endpoint, timeout, delay, result cap), search providers, and reports. API keys belong in `config/secrets.yaml` (gitignored). The default web search source is **self-hosted SearXNG**; paid APIs (Brave, SerpAPI) are optionally switchable.

### Fetcher / robots.txt

`--fetch` respects `robots.txt` by default (`fetcher.respect_robots: true`). If the target page disallows the configured user agent, the URL artifact is skipped (`disallowed by robots.txt`) instead of being fetched anyway, a deliberate design choice for responsible/legal scraping, see also the "Legal" section.

- **Fail-open when robots.txt is unreachable**: if the file itself can't be fetched (timeout, 404, DNS error, ...), fetching is allowed. Only an *explicit* disallow blocks it.
- **Rate limit**: `fetcher.min_delay_per_domain` (default 2s) enforces a minimum pause between requests to the same domain.
- **User agent**: `fetcher.user_agent` identifies the tool to the target server (default `osint-tool/0.1 (+research; contact via config)`).
- **Disabling it**: `respect_robots: false` in `config/default.yaml` (or in an override file passed via `--config`) disables the check entirely. Only use after consultation / legal review.
- **Favicon hashing**: `fetcher.fetch_favicon` (default `true`) hashes the page's favicon (`mmh3`/Shodan-compatible + `md5` fallback) whenever `--fetch` succeeds, no separate flag. `fetcher.favicon_max_bytes` caps the download size (default 512 KB). Set `fetch_favicon: false` to skip it.

### NLP / spaCy Model

`--nlp` uses spaCy for NER. Two config keys control this and should stay in the same language:

- **`nlp.spacy_model`** (default `en_core_web_md`): the spaCy model to load. Must already be downloaded in the environment that's running (see below), the config value alone doesn't install anything.
- **`nlp.keyphrase_lang`** (default `en`): language code for yake's keyphrase extractor; should match `spacy_model`'s language.


**Switching the model:**

1. Edit `nlp.spacy_model` (and `nlp.keyphrase_lang` if the language changes) in `config/default.yaml`, or in an override file passed via `--config`.
2. Download the new model in **every** environment that runs `--nlp`, a config edit on one machine does not affect any other (dev laptop, prod server, CI, ...):

   ```bash
   python -m spacy download <model>
   ```

   Browse available models at the [spaCy models list](https://github.com/explosion/spacy-models) (e.g. `de_core_news_lg` for German, `en_core_web_md`/`en_core_web_lg` for English, larger models are more accurate but slower/heavier).
3. Re-running `scripts/install.sh` on a server reads the *currently* configured `nlp.spacy_model` and downloads that, convenient when (re)deploying after a model switch, no need to edit the script.

If the configured model isn't installed, `--nlp` fails with a clear `RuntimeError` that names the exact `python -m spacy download <model>` command to run, not a silent fallback to a different model.

### WHOIS / RDAP

`--whois` looks up the domain of each `url` artifact via RDAP (no legacy WHOIS/port 43 fallback, see [`docs/interpreting-scores.md`](docs/interpreting-scores.md) for coverage and redaction caveats). Results are cached per domain for the run and rate-limited between requests.

- **`whois.rdap_base_url`** (default `https://rdap.org/domain`): a public RDAP bootstrap/redirect endpoint, no local IANA registry map to maintain. Point this at a different aggregator or a self-hosted bootstrap if needed.
- **`whois.min_delay`** (default 1.0s): minimum pause between RDAP requests.
- **`whois.timeout`** (default 15s).

### Certificate Transparency (crt.sh)

`--certs` looks up each `url` artifact's domain on [crt.sh](https://crt.sh), a free community-run CT log search service. It has **no SLA and is known to be slow or briefly return errors under normal load**, a `--certs` error means "try again," not "no certificates exist" (see[`docs/interpreting-scores.md`](docs/interpreting-scores.md)).

- **`certs.crtsh_base_url`** (default `https://crt.sh`).
- **`certs.min_delay`** (default 2.0s) and **`certs.timeout`** (default 30s, deliberately generous given crt.sh's latency).
- **`certs.max_results`** (default 200): caps how many subdomains/certificate IDs are stored per domain, since popular domains can be logged under thousands of certificates.

## Monitoring / Timeline

`--save` stores every run in SQLite. `--monitor` compares the current run with the last stored run for **the same input file** and shows new/gone targets and links. `--history` lists past runs.

```bash
# Save the first run:
python cli.py artifacts.txt --nlp --search --correlate --save

# Re-run later - what's new?
python cli.py artifacts.txt --nlp --search --correlate --monitor --save

# View history:
python cli.py artifacts.txt --history
```

## MCP / Agentic Session Use

Alongside the classic one-shot `cli.py` (which runs the whole pipeline in a single batch over a static artifact list), the repo ships an **MCP server** (`mcp_server.py`) that exposes the pipeline as tools for an AI agent (Claude Desktop, Claude Code, or any MCP client) to drive **incrementally**: create a case, add one artifact at a time, run one stage at a time, inspect the state, repeat. This suits an interactive investigation where the next step depends on what the last step turned up, rather than a fully-specified batch run.

State for an incremental investigation lives in a **per-case SQLite store** (`cases/<case_id>/case.sqlite`), separate from the classic `--save` database (`data/osint.sqlite`). Each case also gets a `cases/<case_id>/uploads/` directory. The cases root is configurable via `cases.root_dir` in `config/default.yaml` (default `cases`, gitignored).

The server exposes six tools: `create_case`, `add_artifact`, `run_stage`, `get_state`, `generate_report`, `get_audit_log` (see `osint/session/service.py` for the implementation).

### Current limitation: only `fetch` and `localfiles` run incrementally

`run_stage` today only dispatches two stages: **`fetch`** (page text + favicon for `url` artifacts) and **`localfiles`** (text extraction for `file` artifacts). The remaining stages (`whois`, `certs`, `nlp`, `search`, `correlate`, `monitor`) are **not yet wired into the incremental session flow** and remain available only through the classic batch `cli.py` flags. Don't expect to drive WHOIS, CT, NLP, search, or correlation from the MCP session layer yet.

### `file:` artifacts and local documents

The `file` artifact type (prefix-only, `file:leak_doc.pdf`, never auto-detected) points at a document a user or journalist has manually placed in the case's `uploads/` directory. `add_artifact` with `type=file` requires the file to already exist under `<case_dir>/uploads/`. The `localfiles` stage then extracts its text, producing the same `ok`/`text`/`title`/`error` shape as a web fetch, so downstream stages treat local-file text like web-fetched text.

Extractors by extension (`osint/localfiles/extractors/`):

- **`.pdf`** - via the `pdftotext` binary (poppler).
- **`.png` / `.jpg` / `.jpeg` / `.tif` / `.tiff`** - OCR via the `tesseract` binary.
- **`.txt` / `.md` / `.csv` / `.log`** - plain Python read (no external binary).

`pdftotext` and `tesseract` are external binaries, not Python packages - like the spaCy model, they must be installed separately. On a Debian/Ubuntu server `scripts/install.sh` installs `poppler-utils` and `tesseract-ocr` automatically and unconditionally (local-file extraction is core, not MCP-only); the MCP SDK itself is installed only with the `--with-mcp` flag. If a binary is missing, the extractor returns a clean "not installed" error instead of crashing.

Path safety: `resolve_case_path` (`osint/localfiles/loader.py`) resolves the relative path strictly against `<case_dir>/uploads/` and rejects parent traversal (`..`), absolute paths, cross-drive escapes (Windows), NTFS alternate-data-stream / drive syntax (any `:` in the path), and trailing-dot/trailing-space filename tricks Windows would silently rewrite.

The classic CLI can also load `file:` artifacts: `cli.py --fetch` (or `--nlp`) runs the `localfiles` stage over any `file` artifacts in the input, resolving `uploads/` under the directory given by `--case-dir DIR` (default: the input file's own directory).

### Confirmation gate (why every risky stage needs `confirm=True`)

Any stage that touches a network or spawns a subprocess (`fetch`, `localfiles`, plus `whois`/`certs`/`search` reserved for when they're wired in) is blocked by `osint/guardrails.py` unless `run_stage` is called with `confirm=True`. This keeps an MCP-driven agent from silently pivoting to a new target - contacting a third party, spawning a subprocess, or incurring cost - without a human explicitly approving that specific step. It's the practical expression of the **purpose-limitation** and **traceability** obligations described in the ["Legal"](#legal) section: an agent shouldn't widen the scope of a profiling operation on its own.

Paid search providers (`brave`, `serpapi`) are additionally capped per case via `guardrails.max_paid_search_calls_per_case` (default 20); the default self-hosted `searxng` provider is not capped. (This budget applies once `search` is wired into the session flow; see the limitation above.)

### Audit log / chain of custody

Every `run_stage` call - whether it succeeded or was blocked (missing confirmation, unknown stage, budget exhausted) - writes an entry to the case's audit log, readable via `get_audit_log` (`cases/<case_id>/case.sqlite`). This is meant to double as a chain-of-custody record: a reviewable trail of exactly what was looked up, when, and on whose confirmation, suitable for sourcing an investigative story.

### Running the server

```bash
pip install -r requirements-mcp.txt   # or: bash scripts/install.sh --with-mcp
python mcp_server.py                   # stdio transport
```

To use it from an MCP client, add it as an MCP server that runs `python mcp_server.py` from this project's directory (consult your client's MCP configuration docs for the exact file/format - e.g. Claude Desktop's config).

> **Note for readers following MCP SDK examples:** this server targets the **mcp 2.x** SDK (`requirements-mcp.txt` pins `mcp>=2,<3`) and uses the 2.x `MCPServer` API (`from mcp.server.mcpserver import MCPServer`). Many SDK examples online still show the older 1.x `FastMCP` API - that's a real version difference, not a typo; don't mix the two.

## Interpreting Scores

The `--correlate` link score (e.g. `0.80`) and the `--nlp` stylometric similarity score are **not** statistical measures like a correlation coefficient or standard deviation, they're a heuristic weighted evidence tally and a cosine-similarity metric, respectively. See [`docs/interpreting-scores.md`](docs/interpreting-scores.md) for a full explanation and a checklist for reading results responsibly before drawing
conclusions.

## Graph Export (Gephi / Maltego)

`--report graphml` and `--report maltego` export the `--correlate` link network (selectors as nodes, links as edges with `score`/`evidence` attributes), opt-in, not part of the default `--report` (`md,html`). Targets found only via `--search` (web hits, accounts) aren't graphed as separate nodes; see "Shared Targets" in the md/html report for those.

```bash
python cli.py targets.txt --nlp --search --correlate --report md,html,graphml,maltego
```

- **`.graphml`**: open directly in [Gephi](https://gephi.org) or yEd.
- **`.csv`** (from the `maltego` format): a generic `source, source_type, target, target_type, score, evidence` edge list. Maltego has no single fixed CSV schema, use its **Import Graph from Table** wizard and map `source`/ `target` to the two entity columns.

### Extracting a report after the fact

Forgot `graphml`/`maltego` (or any other format) when you ran `--report`, and don't want to re-run `--whois`/`--certs`/`--search` again? If that run also used `--json`, replay it, no network calls, near-instant:

```bash
python cli.py --from-json out.json --report maltego,graphml --out-dir reports
```

`--from-json` replaces the `input` argument entirely and skips `--fetch`/`--whois`/`--certs`/`--nlp`/`--search`/`--correlate`/`--monitor`/ `--save`/`--history` if passed alongside it (with a warning), it only re-renders `--report`/`--json` from the artifacts/correlation data already in the file. If the original run didn't use `--json`, there's currently no way to extract a report from a `--save`d SQLite run without re-running the pipeline.

## Deployment (Vultr VPS)

On a fresh Debian/Ubuntu server:

```bash
git clone <repo> && cd osint_stylometric_search
bash scripts/install.sh            # deps + spaCy model + maigret/holehe + SearXNG (Docker)
# optional: --with-sentiment (torch), --no-searxng, --no-tools, --port N
```

The script creates a `.venv/`, installs everything, and starts **SearXNG** as a Docker container bound to `127.0.0.1:8080` (not publicly reachable), with the JSON API enabled and the rate limiter disabled. Then:

```bash
source .venv/bin/activate
python cli.py your_artifacts.txt --nlp --search --correlate --save --report
```

Security: SearXNG stays local (only the VPS itself can reach it). The generated `server.secret_key` lives in `searxng/settings.yml` (gitignored).

## Legal

Observe EU/GDPR requirements once real people are being profiled/correlated: purpose limitation, data minimization, traceability. For legitimate purposes only (authorized security research, journalism, brand/threat monitoring).

## Support

If you have any questions or problems:

1. Read the detailed README.md
2. GitHub Issues: https://github.com/sublysis/OSIRIS/issues
3. Email: sublysis+support@techmail.at

## License

Licensed under the [European Union Public Licence (EUPL) v1.2](LICENSE).