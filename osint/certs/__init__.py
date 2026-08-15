"""Certificate Transparency stage (module 4c).

Queries crt.sh for `url` artifacts' domains: discovers subdomains via SAN
entries and collects certificate IDs. Results feed into --json/--report and,
via `shared_cert` evidence, into --correlate (two artifacts sharing a
certificate id means the same certificate covers both domains).

crt.sh has no SLA and is known to be slow/flaky - see
docs/interpreting-scores.md for coverage caveats.
"""

from .model import CertResult
from .crtsh import CertClient

__all__ = ["CertResult", "CertClient"]
