from dataclasses import dataclass

DEFAULT_MODEL = "oliverguhr/german-sentiment-bert"


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float


class SentimentAnalyzer:
    """Optional, downstream. Lazily loaded german-sentiment-bert via transformers."""

    def __init__(self, model=DEFAULT_MODEL, max_chars=2000):
        self.model_name = model
        self.max_chars = max_chars
        self._pipe = None

    def _load(self):
        if self._pipe is None:
            try:
                from transformers import pipeline
            except ImportError as e:
                raise RuntimeError("transformers missing - pip install -r requirements-sentiment.txt") from e
            self._pipe = pipeline("sentiment-analysis", model=self.model_name, truncation=True)
        return self._pipe

    def analyze(self, text):
        r = self._load()(text[: self.max_chars])[0]
        return SentimentResult(r["label"], float(r["score"]))

    def analyze_many(self, texts):
        pipe = self._load()
        clipped = [t[: self.max_chars] for t in texts]
        return [SentimentResult(r["label"], float(r["score"])) for r in pipe(clipped)]
