"""Pipeline stage orchestration, extracted out of cli.py so both the CLI
and a future MCP server can drive the same logic. No print()/argparse here -
callers render outcomes however fits their interface (stdout vs. MCP
tool-call return value).
"""

from osint.fetcher import Fetcher
from osint.localfiles import LocalFileLoader


def fetch_urls(url_artifacts, config, results):
    if not url_artifacts:
        return []
    fetcher = Fetcher(config)
    by_value = {r["value"]: r for r in results}
    outcomes = []
    for art in url_artifacts:
        res = fetcher.fetch(art.value)
        entry = by_value.get(art.value, {})
        if res.ok and res.text:
            entry["title"] = res.title
            entry["text"] = res.text
            entry["chars"] = len(res.text)
            if res.favicon_mmh3 is not None or res.favicon_md5 is not None:
                entry["favicon_url"] = res.favicon_url
                entry["favicon_mmh3"] = res.favicon_mmh3
                entry["favicon_md5"] = res.favicon_md5
            outcomes.append({"value": art.value, "ok": True, "status": res.status, "chars": len(res.text)})
        else:
            entry["error"] = res.error or f"HTTP {res.status}"
            outcomes.append({"value": art.value, "ok": False, "error": entry["error"]})
    return outcomes


def load_local_files(file_artifacts, case_dir, config, results):
    if not file_artifacts:
        return []
    loader = LocalFileLoader(config)
    by_value = {r["value"]: r for r in results}
    outcomes = []
    for art in file_artifacts:
        res = loader.load(case_dir, art.value)
        entry = by_value.get(art.value, {})
        if res.ok and res.text:
            entry["title"] = res.title
            entry["text"] = res.text
            entry["chars"] = len(res.text)
            outcomes.append({"value": art.value, "ok": True, "chars": len(res.text)})
        else:
            entry["error"] = res.error
            outcomes.append({"value": art.value, "ok": False, "error": res.error})
    return outcomes
