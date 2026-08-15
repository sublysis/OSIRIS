"""WHOIS/RDAP stage (module 4b).

RDAP-based domain lookups for `url` artifacts (registrar, registrant,
creation/expiry dates). No legacy WHOIS (port 43) fallback - RDAP does not
cover every ccTLD, but needs no extra dependency and stays cross-platform
(see docs/interpreting-scores.md for coverage caveats).

Results are attached per artifact (`entry["whois"]`) and feed into
--json/--report and, via `shared_registrant` evidence, into --correlate.
"""

from .model import WhoisResult
from .rdap import WhoisClient

__all__ = ["WhoisResult", "WhoisClient"]
