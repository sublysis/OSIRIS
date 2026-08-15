"""Correlation stage (module 5).

Merges the enriched artifacts:
- collect_targets: deduplicate targets found on the web; targets shared by
  >=2 seeds are a strong correlation signal.
- build_links: seed<->seed links from shared sources, shared entities,
  stylometry and "seed appears in another document", weighted into a
  confidence score.
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
