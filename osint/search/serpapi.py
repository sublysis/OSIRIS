from .base import SearchError, SearchHit, SearchProvider, requests_or_raise


class SerpapiProvider(SearchProvider):
    """SerpAPI (kostenpflichtig). Key aus config/secrets.yaml."""

    name = "serpapi"
    ENDPOINT = "https://serpapi.com/search.json"

    def __init__(self, config=None):
        super().__init__(config)
        self.api_key = self.config.get("api_key")
        self.engine = self.config.get("engine", "google")
        self.timeout = self.config.get("timeout", 20)

    def search(self, query, limit=20):
        if not self.api_key:
            raise SearchError("SerpAPI-Key fehlt (config/secrets.yaml -> search.providers.serpapi.api_key)")
        requests = requests_or_raise()
        try:
            resp = requests.get(
                self.ENDPOINT,
                params={"engine": self.engine, "q": query, "api_key": self.api_key, "num": limit},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise SearchError(f"SerpAPI Fehler: {e}") from e
        except ValueError as e:
            raise SearchError("SerpAPI lieferte kein JSON") from e

        hits = []
        for r in data.get("organic_results", [])[:limit]:
            hits.append(
                SearchHit(
                    url=r.get("link", ""),
                    title=r.get("title", ""),
                    snippet=r.get("snippet", ""),
                    source="serpapi",
                )
            )
        return hits
