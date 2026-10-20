import base64
import hashlib
import re
import time
from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:
    requests = None

try:
    import trafilatura
except ImportError:
    trafilatura = None

try:
    import mmh3
except ImportError:
    mmh3 = None

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_WS_RE = re.compile(r"\s+")
_ICON_LINK_RE = re.compile(r"<link[^>]+rel=[\"']?(?:shortcut icon|icon)[\"']?[^>]*>", re.IGNORECASE)
_HREF_RE = re.compile(r"href=[\"']([^\"'>]+)[\"']", re.IGNORECASE)


@dataclass
class FetchResult:
    url: str
    ok: bool
    status: int | None = None
    title: str | None = None
    text: str | None = None
    favicon_url: str | None = None
    favicon_mmh3: int | None = None  # Shodan-compatible (http.favicon.hash)
    favicon_md5: str | None = None
    error: str | None = None


class Fetcher:
    def __init__(self, config=None):
        cfg = (config or {}).get("fetcher", {})
        self.user_agent = cfg.get("user_agent", "OSIRIS osint-tool/0.2")
        self.timeout = cfg.get("timeout", 20)
        self.min_delay = cfg.get("min_delay_per_domain", 2.0)
        self.respect_robots = cfg.get("respect_robots", True)
        self.max_bytes = cfg.get("max_bytes", 2_000_000)
        self.fetch_favicon = cfg.get("fetch_favicon", True)
        self.favicon_max_bytes = cfg.get("favicon_max_bytes", 512_000)
        self._last = {}
        self._robots = {}

    def fetch(self, url):
        if requests is None:
            return FetchResult(url, False, error="requests missing - pip install -r requirements.txt")

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return FetchResult(url, False, error="invalid URL")

        if self.respect_robots and not self._allowed(parsed, url):
            return FetchResult(url, False, error="disallowed by robots.txt")

        self._wait(parsed.netloc)

        try:
            resp = requests.get(
                url,
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
                stream=True,
            )
        except requests.RequestException as e:
            return FetchResult(url, False, error=str(e))

        encoding = resp.encoding or "utf-8"
        content = self._read_capped(resp, self.max_bytes)
        html = content.decode(encoding, errors="replace")
        title, text = self._extract(html, url)

        favicon_url = favicon_mmh3 = favicon_md5 = None
        if self.fetch_favicon:
            favicon_url, favicon_mmh3, favicon_md5 = self._fetch_favicon(html, url)

        return FetchResult(
            url, resp.ok, status=resp.status_code, title=title, text=text,
            favicon_url=favicon_url, favicon_mmh3=favicon_mmh3, favicon_md5=favicon_md5,
        )

    def _read_capped(self, resp, max_bytes):
        content = b""
        for chunk in resp.iter_content(8192):
            content += chunk
            if len(content) >= max_bytes:
                break
        resp.close()
        return content

    def _fetch_favicon(self, html, page_url):
        href = self._find_favicon_href(html)
        favicon_url = urljoin(page_url, href) if href else urljoin(page_url, "/favicon.ico")
        parsed = urlparse(favicon_url)

        if parsed.scheme == "data":
            mmh3_hash, md5_hash = self._hash_data_uri(favicon_url)
            return favicon_url, mmh3_hash, md5_hash

        if parsed.scheme not in ("http", "https"):
            return favicon_url, None, None

        if self.respect_robots and not self._allowed(parsed, favicon_url):
            return favicon_url, None, None

        self._wait(parsed.netloc)
        try:
            resp = requests.get(
                favicon_url, headers={"User-Agent": self.user_agent}, timeout=self.timeout, stream=True
            )
        except requests.RequestException:
            return favicon_url, None, None

        if not resp.ok:
            resp.close()
            return favicon_url, None, None

        content = self._read_capped(resp, self.favicon_max_bytes)
        mmh3_hash, md5_hash = self._hash_bytes(content)
        return favicon_url, mmh3_hash, md5_hash

    def _hash_data_uri(self, data_uri):
        header, sep, payload = data_uri.partition(",")
        if not sep or ";base64" not in header:
            return None, None
        try:
            content = base64.b64decode(payload)
        except (ValueError, base64.binascii.Error):
            return None, None
        return self._hash_bytes(content)

    def _hash_bytes(self, content):
        if not content:
            return None, None
        md5_hash = hashlib.md5(content).hexdigest()
        mmh3_hash = mmh3.hash(base64.encodebytes(content)) if mmh3 is not None else None
        return mmh3_hash, md5_hash

    def _find_favicon_href(self, html):
        m = _ICON_LINK_RE.search(html)
        if not m:
            return None
        href = _HREF_RE.search(m.group(0))
        return href.group(1) if href else None

    def _extract(self, html, url):
        title = None
        m = _TITLE_RE.search(html)
        if m:
            title = _WS_RE.sub(" ", _TAG_RE.sub("", m.group(1))).strip()

        text = None
        if trafilatura is not None:
            text = trafilatura.extract(html, url=url, include_comments=False)
        if not text:
            text = self._fallback_text(html)
        return title, text

    def _fallback_text(self, html):
        stripped = _SCRIPT_RE.sub(" ", html)
        stripped = _TAG_RE.sub(" ", stripped)
        return _WS_RE.sub(" ", stripped).strip()

    def _wait(self, netloc):
        now = time.monotonic()
        delta = now - self._last.get(netloc, 0.0)
        if delta < self.min_delay:
            time.sleep(self.min_delay - delta)
        self._last[netloc] = time.monotonic()

    def _allowed(self, parsed, url):
        key = (parsed.scheme, parsed.netloc)
        if key not in self._robots:
            rp = robotparser.RobotFileParser()
            rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
            try:
                rp.read()
            except Exception:
                rp = None  # fail open if robots.txt is unreachable
            self._robots[key] = rp

        rp = self._robots[key]
        if rp is None:
            return True
        return rp.can_fetch(self.user_agent, url)
