#!/usr/bin/env bash
# Installer fuer osint_stylometric_search + SearXNG (Debian/Ubuntu, z. B. Vultr VPS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"
SEARXNG_DIR="$ROOT/searxng"

WITH_SENTIMENT=0
INSTALL_SEARXNG=1
INSTALL_TOOLS=1
SEARXNG_PORT=8080

usage() {
  cat <<'EOF'
Usage: bash scripts/install.sh [OPTIONS]

  --with-sentiment   zusaetzlich Sentiment-Deps (transformers, torch) installieren
  --no-searxng       SearXNG-Setup ueberspringen
  --no-tools         maigret/holehe nicht installieren
  --port N           SearXNG-Port (default 8080, nur an 127.0.0.1 gebunden)
  -h, --help         diese Hilfe
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --with-sentiment) WITH_SENTIMENT=1 ;;
    --no-searxng) INSTALL_SEARXNG=0 ;;
    --no-tools) INSTALL_TOOLS=0 ;;
    --port) shift; SEARXNG_PORT="$1" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unbekannte Option: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

log() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "Dieses Script unterstuetzt nur Debian/Ubuntu (apt)." >&2
  exit 1
fi

log "System-Pakete installieren"
$SUDO apt-get update -y
$SUDO apt-get install -y python3 python3-venv python3-pip git curl openssl build-essential

log "Python-venv anlegen: $VENV"
python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --upgrade pip wheel

log "Core-Dependencies"
pip install -r "$ROOT/requirements.txt"

log "NLP-Dependencies (spaCy, scikit-learn, yake)"
pip install -r "$ROOT/requirements-nlp.txt"
python -m spacy download de_core_news_lg

if [ "$WITH_SENTIMENT" -eq 1 ]; then
  log "Sentiment-Dependencies (transformers, torch) - das dauert"
  pip install -r "$ROOT/requirements-sentiment.txt"
fi

if [ "$INSTALL_TOOLS" -eq 1 ]; then
  log "OSINT-Tools (maigret, holehe)"
  pip install maigret holehe
fi

if [ "$INSTALL_SEARXNG" -eq 1 ]; then
  if ! command -v docker >/dev/null 2>&1; then
    log "Docker installieren"
    $SUDO apt-get install -y docker.io
    $SUDO systemctl enable --now docker
  fi

  mkdir -p "$SEARXNG_DIR"
  if [ ! -f "$SEARXNG_DIR/settings.yml" ]; then
    log "SearXNG-Config erzeugen (JSON aktiviert, Limiter aus)"
    SECRET="$(openssl rand -hex 32)"
    cat > "$SEARXNG_DIR/settings.yml" <<EOF
use_default_settings: true
server:
  secret_key: "$SECRET"
  limiter: false
  image_proxy: false
search:
  formats:
    - html
    - json
EOF
  else
    log "SearXNG-Config existiert bereits - unveraendert"
  fi

  log "SearXNG-Container starten (nur an 127.0.0.1:$SEARXNG_PORT)"
  $SUDO docker rm -f searxng >/dev/null 2>&1 || true
  $SUDO docker run -d --name searxng --restart unless-stopped \
    -p "127.0.0.1:$SEARXNG_PORT:8080" \
    -v "$SEARXNG_DIR:/etc/searxng" \
    searxng/searxng:latest

  log "SearXNG-Healthcheck (JSON-API)"
  ok=0
  for _ in $(seq 1 15); do
    if curl -fsS "http://127.0.0.1:$SEARXNG_PORT/search?q=test&format=json" >/dev/null 2>&1; then
      ok=1; break
    fi
    sleep 2
  done
  if [ "$ok" -eq 1 ]; then
    echo "SearXNG JSON-API erreichbar."
  else
    echo "WARN: SearXNG antwortet noch nicht auf die JSON-API. 'docker logs searxng' pruefen." >&2
  fi
fi

log "Fertig"
cat <<EOF

Naechste Schritte:
  source $VENV/bin/activate
  python cli.py deine_artefakte.txt --nlp --search --correlate --save --report

SearXNG laeuft unter http://127.0.0.1:$SEARXNG_PORT (entspricht dem Default in config/default.yaml).
Bezahl-APIs optional: config/secrets.yaml aus config/secrets.example.yaml erstellen.
EOF
