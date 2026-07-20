import re
from dataclasses import dataclass, field
from enum import Enum


class ArtifactType(str, Enum):
    URL = "url"
    EMAIL = "email"
    USERNAME = "username"
    NAME = "name"
    UNKNOWN = "unknown"


@dataclass
class Artifact:
    type: ArtifactType
    value: str
    raw: str
    meta: dict = field(default_factory=dict)


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9-]+\.)+[a-z]{2,}(/\S*)?$", re.IGNORECASE)
EXPLICIT_RE = re.compile(r"^(url|email|username|name)\s*:\s*(.+)$", re.IGNORECASE)

_TYPES = {t.value: t for t in ArtifactType}


def classify_line(raw, comment_prefix="#"):
    line = raw.strip()
    if not line or line.startswith(comment_prefix):
        return None

    forced = None
    m = EXPLICIT_RE.match(line)
    if m:
        forced = _TYPES[m.group(1).lower()]
        line = m.group(2).strip()

    line = _unquote(line)
    art_type = forced or _detect(line)
    return Artifact(art_type, _normalize(art_type, line), raw.rstrip("\n"))


def _detect(text):
    if EMAIL_RE.match(text):
        return ArtifactType.EMAIL
    if URL_SCHEME_RE.match(text) or DOMAIN_RE.match(text):
        return ArtifactType.URL
    if " " in text:
        return ArtifactType.NAME
    return ArtifactType.USERNAME


def _normalize(art_type, value):
    if art_type == ArtifactType.USERNAME:
        return value.lstrip("@")
    if art_type == ArtifactType.URL and not URL_SCHEME_RE.match(value):
        return "https://" + value
    if art_type == ArtifactType.EMAIL:
        return value.lower()
    return value


def _unquote(text):
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1].strip()
    return text
