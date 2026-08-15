from dataclasses import dataclass, field


@dataclass
class CertResult:
    domain: str
    ok: bool
    subdomains: list = field(default_factory=list)
    certificate_ids: list = field(default_factory=list)
    cert_count: int = 0  # total distinct certs seen, before any capping
    error: str | None = None

    def to_dict(self):
        return {
            "domain": self.domain,
            "ok": self.ok,
            "subdomains": self.subdomains,
            "certificate_ids": self.certificate_ids,
            "cert_count": self.cert_count,
            "error": self.error,
        }
