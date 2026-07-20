"""Korrelations-Stufe (Modul 5).

Fuehrt die angereicherten Artefakte zusammen:
- collect_targets: im Netz gefundene Ziele deduplizieren; von >=2 Seeds geteilte
  Ziele sind ein starkes Korrelationssignal.
- build_links: Seed<->Seed-Verknuepfungen aus geteilten Quellen, geteilten
  Entitaeten, Stilometrie und "Seed erscheint in fremdem Dokument", gewichtet
  zu einem Konfidenz-Score.
"""

from .linker import build_links, collect_targets
from .model import CorrelationResult, Evidence, Link, Target

__all__ = ["correlate", "CorrelationResult", "Evidence", "Link", "Target", "collect_targets", "build_links"]


def correlate(artifacts, stylometry=None, config=None):
    config = config or {}
    targets = collect_targets(artifacts)
    targets.sort(key=lambda t: (t.seed_count, len(t.sources)), reverse=True)
    links = build_links(artifacts, stylometry, config)
    return CorrelationResult(targets, links)
