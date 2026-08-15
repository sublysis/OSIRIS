"""Search stage (module 4).

Provider (free<->paid is pure config, search.default_provider):
- searxng.py  : self-hosted (default)
- brave.py    : free tier (API key optional)
- serpapi.py  : paid (optional)
- tools/      : subprocess wrappers for maigret, holehe (availability-gated)

All providers raise SearchError on problems (provider down, key missing).
"""

from .base import SearchError, SearchHit, SearchProvider
from .registry import PROVIDERS, get_provider

__all__ = ["SearchError", "SearchHit", "SearchProvider", "PROVIDERS", "get_provider"]
