import time

try:
    import requests
except ImportError:
    requests = None

from .model import CertResult


def _looks_like_hostname(value):
    v = (value or "").strip().lower()
    if not v or "@" in v or " " in v or "." not in v:
        return False
    return True


def _parse(domain, entries, max_results):
    cert_ids = set()
    subdomains = set()
    for entry in entries:
        cid = entry.get("id")
        if cid is not None:
            cert_ids.add(cid)
        for name in (entry.get("name_value") or "").split("\n"):
            if _looks_like_hostname(name):
                subdomains.add(name.strip().lower())

    return CertResult(
        domain=domain,
        ok=True,
        subdomains=sorted(subdomains)[:max_results],
        certificate_ids=sorted(cert_ids)[:max_results],
        cert_count=len(cert_ids),
    )


class CertClient:
    """Certificate Transparency lookup via crt.sh, with per-run caching and rate-limiting.

    crt.sh is a free community service backed by a large Postgres database -
    it has no SLA and is known to return slow responses, timeouts, or bare
    502s under load (observed directly while building this client). Callers
    should treat a --certs error as "try again later," not "no certs exist."
    See docs/interpreting-scores.md for coverage caveats.
    """

    def __init__(self, config=None):
        cfg = (config or {}).get("certs", {}) or {}
        self.base_url = cfg.get("crtsh_base_url", "https://crt.sh").rstrip("/")
        self.timeout = cfg.get("timeout", 30)
        self.min_delay = cfg.get("min_delay", 2.0)
        self.max_results = cfg.get("max_results", 200)
        self.user_agent = cfg.get("user_agent", "osint-tool/0.1")
        self._cache = {}
        self._last_request = 0.0

    def lookup(self, domain):
        domain = (domain or "").strip().lower()
        if not domain:
            return CertResult(domain, False, error="empty domain")
        if domain in self._cache:
            return self._cache[domain]
        result = self._fetch(domain)
        self._cache[domain] = result
        return result

    def _fetch(self, domain):
        if requests is None:
            return CertResult(domain, False, error="requests missing - pip install -r requirements.txt")

        self._wait()
        try:
            resp = requests.get(
                f"{self.base_url}/",
                params={"q": domain, "output": "json"},
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            return CertResult(domain, False, error=str(e))

        if resp.status_code != 200:
            return CertResult(
                domain, False,
                error=f"HTTP {resp.status_code} (crt.sh is a community service, often unstable under load)",
            )

        try:
            data = resp.json()
        except ValueError:
            return CertResult(domain, False, error="crt.sh returned no JSON - known-flaky, try again later")

        try:
            return _parse(domain, data, self.max_results)
        except Exception as e:
            return CertResult(domain, False, error=f"crt.sh parse error: {e}")

    def _wait(self):
        now = time.monotonic()
        delta = now - self._last_request
        if delta < self.min_delay:
            time.sleep(self.min_delay - delta)
        self._last_request = time.monotonic()
