import re
from dataclasses import dataclass

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
HANDLE_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_]{2,}")
URL_RE = re.compile(r"https?://[^\s<>\"']+")

DEFAULT_MODEL = "de_core_news_lg"

_SPACY_LABELS = {
    "PER": "PERSON",
    "PERSON": "PERSON",
    "ORG": "ORG",
    "LOC": "LOC",
    "GPE": "LOC",
    "MISC": "MISC",
}


@dataclass(frozen=True)
class Entity:
    label: str
    text: str
    start: int = -1
    end: int = -1


_URL_TRAILING = ".,;:!?)]}'\""


def extract_regex_entities(text):
    ents = []
    for m in EMAIL_RE.finditer(text):
        ents.append(Entity("EMAIL", m.group(), m.start(), m.end()))
    for m in HANDLE_RE.finditer(text):
        ents.append(Entity("HANDLE", m.group(), m.start(), m.end()))
    for m in URL_RE.finditer(text):
        val = m.group().rstrip(_URL_TRAILING)
        ents.append(Entity("URL", val, m.start(), m.start() + len(val)))
    return ents


class EntityExtractor:
    def __init__(self, model=DEFAULT_MODEL):
        self.model_name = model
        self._nlp = None

    def _load(self):
        if self._nlp is None:
            try:
                import spacy
            except ImportError as e:
                raise RuntimeError("spaCy fehlt - pip install -r requirements-nlp.txt") from e
            try:
                self._nlp = spacy.load(self.model_name)
            except OSError as e:
                raise RuntimeError(
                    f"spaCy-Modell '{self.model_name}' fehlt - "
                    f"python -m spacy download {self.model_name}"
                ) from e
        return self._nlp

    def extract(self, text, use_spacy=True):
        ents = extract_regex_entities(text)
        if use_spacy:
            doc = self._load()(text)
            for e in doc.ents:
                label = _SPACY_LABELS.get(e.label_, e.label_)
                ents.append(Entity(label, e.text, e.start_char, e.end_char))
        return _dedupe(ents)


def _dedupe(ents):
    seen = set()
    out = []
    for e in ents:
        key = (e.label, e.text.lower())
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out
