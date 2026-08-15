from abc import ABC, abstractmethod
from dataclasses import dataclass


class SearchError(RuntimeError):
    """Provider unreachable, key missing, or invalid response."""


@dataclass
class SearchHit:
    url: str
    title: str = ""
    snippet: str = ""
    source: str = ""

    def to_dict(self):
        return {"url": self.url, "title": self.title, "snippet": self.snippet, "source": self.source}


class SearchProvider(ABC):
    name = "base"

    def __init__(self, config=None):
        self.config = config or {}

    @abstractmethod
    def search(self, query, limit=20):
        """Returns a list of SearchHit. Raises SearchError on problems."""
        raise NotImplementedError


def requests_or_raise():
    try:
        import requests
    except ImportError as e:
        raise SearchError("requests missing - pip install -r requirements.txt") from e
    return requests
