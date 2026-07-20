"""NLP-Stufe (Modul 3): NER, Keyphrases, Stilometrie, (optional) Sentiment.

Alle schweren Abhaengigkeiten (spaCy, yake, scikit-learn, transformers) werden
lazy geladen - der Paket-Import bleibt leichtgewichtig. Fehlt eine Dependency,
wirft die jeweilige Methode einen RuntimeError mit Installationshinweis; die
Regex-NER und basic_features laufen ganz ohne Deps.

Benoetigt requirements-nlp.txt (+ python -m spacy download de_core_news_lg).
"""

from .keyphrases import Keyphrase, KeyphraseExtractor
from .ner import Entity, EntityExtractor, extract_regex_entities
from .sentiment import SentimentAnalyzer, SentimentResult
from .stylometry import StylometryModel, basic_features

__all__ = [
    "Entity",
    "EntityExtractor",
    "extract_regex_entities",
    "Keyphrase",
    "KeyphraseExtractor",
    "StylometryModel",
    "basic_features",
    "SentimentAnalyzer",
    "SentimentResult",
]
