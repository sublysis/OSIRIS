"""Such-Stufe (Modul 4).

Provider (kostenlos<->bezahlt = reine Config, search.default_provider):
- searxng.py  : self-hosted (Standard)
- brave.py    : Free-Tier (API-Key optional)
- serpapi.py  : Bezahl (optional)
- tools/      : Subprocess-Wrapper fuer maigret, holehe (availability-gated)

Alle Provider werfen SearchError bei Problemen (Provider down, Key fehlt).
"""

from .base import SearchError, SearchHit, SearchProvider
from .registry import PROVIDERS, get_provider

__all__ = ["SearchError", "SearchHit", "SearchProvider", "PROVIDERS", "get_provider"]
