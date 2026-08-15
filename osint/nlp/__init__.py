"""NLP stage (module 3): NER, keyphrases, stylometry, (optional) sentiment.

All heavy dependencies (spaCy, yake, scikit-learn, transformers) are lazily
loaded - the package import stays lightweight. If a dependency is missing,
the respective method raises a RuntimeError with an installation hint; the
regex NER and basic_features run entirely without deps.

Requires requirements-nlp.txt (+ python -m spacy download de_core_news_lg).
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
