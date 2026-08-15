import time
from urllib.parse import quote

try:
    import requests
except ImportError:
    requests = None

from .model import WhoisResult

# Substrings seen in GDPR/privacy-proxy redacted RDAP registrant fields.
# Deliberately conservative: a false negative (treating a real name as
# non-redacted) is worse for correlation quality than a false positive here.
_REDACTION_MARKERS = (
    "redacted", "privacy", "protect", "not disclosed", "withheld",
    "gdpr", "data protected", "whoisguard", "proxy", "on behalf of",
    "non-public", "undisclosed",
)


def _looks_redacted(value):
    if not value:
        return False
    v = value.lower()
    return any(m in v for m in _REDACTION_MARKERS)


def _vcard_get(vcard_array, name):
    if not vcard_array or len(vcard_array) < 2:
        return None
    for entry in vcard_array[1]:
        if entry and len(entry) >= 4 and entry[0] == name:
            return entry[3]
    return None


def _registrar_name(entity):
    vcard = entity.get("vcardArray")
    fn = _vcard_get(vcard, "fn")
    if fn:
        return fn
    public_ids = entity.get("publicIds") or []
    if public_ids:
        return public_ids[0].get("identifier")
    return None


def parse_rdap(domain, data):
    events = {e.get("eventAction"): e.get("eventDate") for e in data.get("events", []) if e.get("eventAction")}
    created = events.get("registration")
    updated = events.get("last changed") or events.get("last update of RDAP database")
    expires = events.get("expiration")

    registrar = None
    registrant_org = None
    registrant_email = None
    redacted = False

    for ent in data.get("entities", []):
        roles = ent.get("roles", [])

        if "registrar" in roles and not registrar:
            registrar = _registrar_name(ent)

        if "registrant" in roles:
            vcard = ent.get("vcardArray")
            org = _vcard_get(vcard, "fn")
            email = _vcard_get(vcard, "email")
            if org:
                if _looks_redacted(org):
                    redacted = True
                else:
                    registrant_org = org
            if email:
                if _looks_redacted(email):
                    redacted = True
                else:
                    registrant_email = email

    nameservers = [ns.get("ldhName") for ns in data.get("nameservers", []) if ns.get("ldhName")]

    return WhoisResult(
        domain=domain,
        ok=True,
        registrar=registrar,
        registrant_org=registrant_org,
        registrant_email=registrant_email,
        created=created,
        updated=updated,
        expires=expires,
        status=data.get("status", []),
        nameservers=nameservers,
        redacted=redacted,
    )


class WhoisClient:
    """RDAP-based domain lookup, with per-run caching and rate-limiting.

    Uses rdap.org as a bootstrap/redirect endpoint so no local IANA registry
    map needs to be maintained. No legacy WHOIS (port 43) fallback - some
    ccTLDs have no RDAP server yet, see docs/interpreting-scores.md.
    """

    def __init__(self, config=None):
        cfg = (config or {}).get("whois", {}) or {}
        self.base_url = cfg.get("rdap_base_url", "https://rdap.org/domain").rstrip("/")
        self.timeout = cfg.get("timeout", 15)
        self.min_delay = cfg.get("min_delay", 1.0)
        self.user_agent = cfg.get("user_agent", "osint-tool/0.1")
        self._cache = {}
        self._last_request = 0.0

    def lookup(self, domain):
        domain = (domain or "").strip().lower()
        if not domain:
            return WhoisResult(domain, False, error="empty domain")
        if domain in self._cache:
            return self._cache[domain]
        result = self._fetch(domain)
        self._cache[domain] = result
        return result

    def _fetch(self, domain):
        if requests is None:
            return WhoisResult(domain, False, error="requests missing - pip install -r requirements.txt")

        self._wait()
        try:
            resp = requests.get(
                f"{self.base_url}/{quote(domain)}",
                headers={"User-Agent": self.user_agent, "Accept": "application/rdap+json"},
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            return WhoisResult(domain, False, error=str(e))

        if resp.status_code == 404:
            return WhoisResult(domain, False, error="domain not found in RDAP")
        if not resp.ok:
            return WhoisResult(domain, False, error=f"HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError:
            return WhoisResult(domain, False, error="RDAP returned no JSON")

        try:
            return parse_rdap(domain, data)
        except Exception as e:
            return WhoisResult(domain, False, error=f"RDAP parse error: {e}")

    def _wait(self):
        now = time.monotonic()
        delta = now - self._last_request
        if delta < self.min_delay:
            time.sleep(self.min_delay - delta)
        self._last_request = time.monotonic()
