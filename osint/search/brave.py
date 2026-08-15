from .base import SearchError, SearchHit, SearchProvider, requests_or_raise


class BraveProvider(SearchProvider):
    """Brave Search API (free tier possible). Key from config/secrets.yaml."""

    name = "brave"
    ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, config=None):
        super().__init__(config)
        self.api_key = self.config.get("api_key")
        self.timeout = self.config.get("timeout", 15)

    def search(self, query, limit=20):
        if not self.api_key:
            raise SearchError("Brave API key missing (config/secrets.yaml -> search.providers.brave.api_key)")
        requests = requests_or_raise()
        try:
            resp = requests.get(
                self.ENDPOINT,
                params={"q": query, "count": min(limit, 20)},
                headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise SearchError(f"Brave API error: {e}") from e
        except ValueError as e:
            raise SearchError("Brave returned no JSON") from e

        hits = []
        for r in data.get("web", {}).get("results", [])[:limit]:
            hits.append(
                SearchHit(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    snippet=r.get("description", ""),
                    source="brave",
                )
            )
        return hits
