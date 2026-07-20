from .base import SearchError, SearchHit, SearchProvider, requests_or_raise


class SearxngProvider(SearchProvider):
    """Self-hosted SearXNG (Standard). Instanz muss 'format: json' erlauben."""

    name = "searxng"

    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = self.config.get("base_url", "http://localhost:8080").rstrip("/")
        self.categories = self.config.get("categories")
        self.engines = self.config.get("engines")
        self.timeout = self.config.get("timeout", 15)

    def search(self, query, limit=20):
        requests = requests_or_raise()
        params = {"q": query, "format": "json"}
        if self.categories:
            params["categories"] = self.categories
        if self.engines:
            params["engines"] = self.engines
        try:
            resp = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "osint-tool/0.1"},
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise SearchError(f"SearXNG nicht erreichbar ({self.base_url}): {e}") from e
        except ValueError as e:
            raise SearchError(
                "SearXNG lieferte kein JSON - ist 'json' in der SearXNG-Config unter search.formats erlaubt?"
            ) from e

        hits = []
        for r in data.get("results", [])[:limit]:
            hits.append(
                SearchHit(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    snippet=r.get("content", ""),
                    source=r.get("engine", "searxng"),
                )
            )
        return hits
