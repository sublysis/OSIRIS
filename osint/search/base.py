from abc import ABC, abstractmethod
from dataclasses import dataclass


class SearchError(RuntimeError):
    """Provider nicht erreichbar, Key fehlt, oder ungueltige Antwort."""


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
        """Gibt eine Liste von SearchHit zurueck. Wirft SearchError bei Problemen."""
        raise NotImplementedError


def requests_or_raise():
    try:
        import requests
    except ImportError as e:
        raise SearchError("requests fehlt - pip install -r requirements.txt") from e
    return requests
