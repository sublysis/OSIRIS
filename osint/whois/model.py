from dataclasses import dataclass, field


@dataclass
class WhoisResult:
    domain: str
    ok: bool
    registrar: str | None = None
    registrant_org: str | None = None
    registrant_email: str | None = None
    created: str | None = None
    updated: str | None = None
    expires: str | None = None
    status: list = field(default_factory=list)
    nameservers: list = field(default_factory=list)
    redacted: bool = False
    error: str | None = None

    def to_dict(self):
        return {
            "domain": self.domain,
            "ok": self.ok,
            "registrar": self.registrar,
            "registrant_org": self.registrant_org,
            "registrant_email": self.registrant_email,
            "created": self.created,
            "updated": self.updated,
            "expires": self.expires,
            "status": self.status,
            "nameservers": self.nameservers,
            "redacted": self.redacted,
            "error": self.error,
        }
