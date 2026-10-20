#!/usr/bin/env bash
# Installer for osint_stylometric_search + SearXNG (Debian/Ubuntu, e.g. Vultr VPS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"
SEARXNG_DIR="$ROOT/searxng"

WITH_SENTIMENT=0
WITH_SENTIMENT_GPU=0
WITH_MCP=0
INSTALL_SEARXNG=1
INSTALL_TOOLS=1
SEARXNG_PORT=8080

usage() {
  cat <<'EOF'
Usage: bash scripts/install.sh [OPTIONS]

  --with-sentiment     also install sentiment deps, CPU-only (transformers, torch)
  --with-sentiment-gpu same as --with-sentiment, but with CUDA/GPU torch (several GB)
  --with-mcp           also install MCP server deps (requirements-mcp.txt)
  --no-searxng       skip SearXNG setup
  --no-tools         don't install maigret/holehe
  --port N           SearXNG port (default 8080, bound to 127.0.0.1 only)
  -h, --help         this help
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --with-sentiment) WITH_SENTIMENT=1 ;;
    --with-sentiment-gpu) WITH_SENTIMENT_GPU=1 ;;
    --with-mcp) WITH_MCP=1 ;;
    --no-searxng) INSTALL_SEARXNG=0 ;;
    --no-tools) INSTALL_TOOLS=0 ;;
    --port) shift; SEARXNG_PORT="$1" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

log() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This script only supports Debian/Ubuntu (apt)." >&2
  exit 1
fi

log "Installing system packages"
$SUDO apt-get update -y
$SUDO apt-get install -y python3 python3-venv python3-pip git curl openssl build-essential poppler-utils tesseract-ocr

log "Creating Python venv: $VENV"
python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --upgrade pip wheel

log "Core dependencies"
pip install -r "$ROOT/requirements.txt"

log "NLP dependencies (spaCy, scikit-learn, yake)"
pip install -r "$ROOT/requirements-nlp.txt"

SPACY_MODEL="$(cd "$ROOT" && python3 -c "from osint.config import load_config; print(load_config().get('nlp', {}).get('spacy_model', ''))")"
if [ -z "$SPACY_MODEL" ]; then
  echo "WARN: could not determine nlp.spacy_model from config/default.yaml, falling back to de_core_news_lg" >&2
  SPACY_MODEL="de_core_news_lg"
fi
log "Downloading spaCy model: $SPACY_MODEL (from config/default.yaml nlp.spacy_model)"
python -m spacy download "$SPACY_MODEL"

if [ "$WITH_SENTIMENT_GPU" -eq 1 ]; then
  log "Sentiment dependencies (transformers, torch+CUDA) - this takes a while"
  pip install -r "$ROOT/requirements-sentiment-gpu.txt"
elif [ "$WITH_SENTIMENT" -eq 1 ]; then
  log "Sentiment dependencies (transformers, torch, CPU-only) - this takes a while"
  pip install -r "$ROOT/requirements-sentiment.txt"
fi

if [ "$WITH_MCP" -eq 1 ]; then
  log "MCP server dependencies"
  pip install -r "$ROOT/requirements-mcp.txt"
fi

if [ "$INSTALL_TOOLS" -eq 1 ]; then
  log "OSINT tools (maigret, holehe)"
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
    log "Generating SearXNG config (JSON enabled, limiter off)"
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
    log "SearXNG config already exists - unchanged"
  fi

  log "Starting SearXNG container (bound to 127.0.0.1:$SEARXNG_PORT only)"
  $SUDO docker rm -f searxng >/dev/null 2>&1 || true
  $SUDO docker run -d --name searxng --restart unless-stopped \
    -p "127.0.0.1:$SEARXNG_PORT:8080" \
    -v "$SEARXNG_DIR:/etc/searxng" \
    searxng/searxng:latest

  log "SearXNG health check (JSON API)"
  ok=0
  for _ in $(seq 1 15); do
    if curl -fsS "http://127.0.0.1:$SEARXNG_PORT/search?q=test&format=json" >/dev/null 2>&1; then
      ok=1; break
    fi
    sleep 2
  done
  if [ "$ok" -eq 1 ]; then
    echo "SearXNG JSON API reachable."
  else
    echo "WARN: SearXNG isn't answering the JSON API yet. Check 'docker logs searxng'." >&2
  fi
fi

log "Done"
cat <<EOF

Next steps:
  source $VENV/bin/activate
  python cli.py your_artifacts.txt --nlp --search --whois --correlate --save --report

SearXNG is running at http://127.0.0.1:$SEARXNG_PORT (matches the default in config/default.yaml).
Paid APIs optional: create config/secrets.yaml from config/secrets.example.yaml.
EOF