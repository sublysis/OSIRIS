import re
import time
from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None

try:
    import trafilatura
except ImportError:
    trafilatura = None

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_WS_RE = re.compile(r"\s+")


@dataclass
class FetchResult:
    url: str
    ok: bool
    status: int | None = None
    title: str | None = None
    text: str | None = None
    error: str | None = None


class Fetcher:
    def __init__(self, config=None):
        cfg = (config or {}).get("fetcher", {})
        self.user_agent = cfg.get("user_agent", "osint-tool/0.1")
        self.timeout = cfg.get("timeout", 20)
        self.min_delay = cfg.get("min_delay_per_domain", 2.0)
        self.respect_robots = cfg.get("respect_robots", True)
        self.max_bytes = cfg.get("max_bytes", 2_000_000)
        self._last = {}
        self._robots = {}

    def fetch(self, url):
        if requests is None:
            return FetchResult(url, False, error="requests fehlt - pip install -r requirements.txt")

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return FetchResult(url, False, error="ungueltige URL")

        if self.respect_robots and not self._allowed(parsed, url):
            return FetchResult(url, False, error="durch robots.txt verboten")

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
        content = self._read_capped(resp)
        html = content.decode(encoding, errors="replace")
        title, text = self._extract(html, url)
        return FetchResult(url, resp.ok, status=resp.status_code, title=title, text=text)

    def _read_capped(self, resp):
        content = b""
        for chunk in resp.iter_content(8192):
            content += chunk
            if len(content) >= self.max_bytes:
                break
        resp.close()
        return content

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
                rp = None  # fail open, wenn robots.txt nicht erreichbar
            self._robots[key] = rp

        rp = self._robots[key]
        if rp is None:
            return True
        return rp.can_fetch(self.user_agent, url)
