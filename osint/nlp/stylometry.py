import re
from collections import Counter
from dataclasses import dataclass

# Themenunabhaengige, stilrelevante Funktionswoerter (DE + etwas EN).
FUNCTION_WORDS = [
    "der", "die", "das", "und", "oder", "aber", "weil", "dass", "wenn", "als", "wie",
    "ich", "du", "er", "sie", "es", "wir", "ihr", "man", "mein", "dein", "sein",
    "ein", "eine", "einen", "dem", "den", "des", "zu", "zur", "zum", "in", "im", "auf",
    "mit", "von", "fuer", "ohne", "auch", "noch", "nur", "schon", "sehr", "doch", "ja",
    "nicht", "kein", "keine", "the", "and", "or", "but", "is", "are", "was", "were",
]

PUNCT = list(".,;:!?-()\"'")

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_SENT_RE = re.compile(r"[.!?]+")


def basic_features(text):
    """Handgemachte Stil-Statistiken, reines Python (keine Deps)."""
    words = _WORD_RE.findall(text.lower())
    n = len(words) or 1
    chars = len(text) or 1
    sentences = [s for s in _SENT_RE.split(text) if s.strip()]

    feats = {
        "n_words": len(words),
        "avg_word_len": sum(len(w) for w in words) / n,
        "type_token_ratio": len(set(words)) / n,
        "avg_sentence_len": len(words) / (len(sentences) or 1),
        "uppercase_ratio": sum(1 for c in text if c.isupper()) / chars,
        "digit_ratio": sum(1 for c in text if c.isdigit()) / chars,
    }
    for p in PUNCT:
        feats[f"punct_{p}"] = text.count(p) / chars
    counts = Counter(words)
    for fw in FUNCTION_WORDS:
        feats[f"fw_{fw}"] = counts.get(fw, 0) / n
    return feats


@dataclass
class StylometryModel:
    """char-n-gram TF-IDF + Kosinus-Aehnlichkeit als Autor-Fingerabdruck."""

    ngram_range: tuple = (2, 4)
    max_features: int = 2000

    def __post_init__(self):
        self._vec = None
        self._matrix = None
        self._labels = None

    def fit(self, texts, labels=None):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError as e:
            raise RuntimeError("scikit-learn fehlt - pip install -r requirements-nlp.txt") from e
        self._vec = TfidfVectorizer(
            analyzer="char_wb", ngram_range=self.ngram_range, max_features=self.max_features
        )
        self._matrix = self._vec.fit_transform(texts)
        self._labels = list(labels) if labels is not None else list(range(len(texts)))
        return self

    def similarity_matrix(self):
        from sklearn.metrics.pairwise import cosine_similarity

        return cosine_similarity(self._matrix)

    def most_similar_pairs(self, threshold=0.0, top=None):
        sim = self.similarity_matrix()
        pairs = []
        n = sim.shape[0]
        for i in range(n):
            for j in range(i + 1, n):
                score = float(sim[i, j])
                if score >= threshold:
                    pairs.append((self._labels[i], self._labels[j], score))
        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs[:top] if top else pairs
