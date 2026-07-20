from urllib.parse import urlparse


def canonical_domain(url_or_domain):
    s = (url_or_domain or "").strip().lower()
    if not s:
        return ""
    if "://" not in s:
        s = "http://" + s
    netloc = urlparse(s).netloc
    netloc = netloc.split("@")[-1].split(":")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def canonical_url(url):
    s = (url or "").strip()
    if "://" not in s:
        s = "http://" + s
    p = urlparse(s)
    netloc = p.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = p.path.rstrip("/")
    return f"{p.scheme or 'http'}://{netloc}{path}".lower()


def canonical_handle(handle):
    return (handle or "").lstrip("@").strip().lower()
