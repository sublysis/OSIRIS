import copy
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"


def load_config(path=None):
    if yaml is None:
        raise RuntimeError("PyYAML missing - run 'pip install -r requirements.txt'")
    data = _read(DEFAULT_CONFIG)
    secrets = PROJECT_ROOT / "config" / "secrets.yaml"
    if secrets.exists():
        data = _merge(data, _read(secrets))
    if path:
        data = _merge(data, _read(Path(path)))
    return data


def _read(p):
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out
