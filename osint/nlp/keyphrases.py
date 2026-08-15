from dataclasses import dataclass


@dataclass(frozen=True)
class Keyphrase:
    text: str
    score: float


class KeyphraseExtractor:
    """YAKE-based. Lower score = more relevant."""

    def __init__(self, lang="de", max_ngram=3, top=20):
        self.lang = lang
        self.max_ngram = max_ngram
        self.top = top
        self._kw = None

    def _load(self):
        if self._kw is None:
            try:
                import yake
            except ImportError as e:
                raise RuntimeError("yake missing - pip install -r requirements-nlp.txt") from e
            self._kw = yake.KeywordExtractor(lan=self.lang, n=self.max_ngram, top=self.top)
        return self._kw

    def extract(self, text):
        kw = self._load()
        return [Keyphrase(phrase, float(score)) for phrase, score in kw.extract_keywords(text)]
