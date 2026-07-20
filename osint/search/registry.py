from .base import SearchError
from .brave import BraveProvider
from .searxng import SearxngProvider
from .serpapi import SerpapiProvider

PROVIDERS = {cls.name: cls for cls in (SearxngProvider, BraveProvider, SerpapiProvider)}


def get_provider(config, name=None):
    search_cfg = config.get("search", {})
    name = name or search_cfg.get("default_provider", "searxng")
    cls = PROVIDERS.get(name)
    if cls is None:
        raise SearchError(f"unbekannter Provider '{name}' (verfuegbar: {', '.join(PROVIDERS)})")
    provider_cfg = search_cfg.get("providers", {}).get(name, {})
    return cls(provider_cfg)
