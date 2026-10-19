from .base import Extractor, ExtractorResult


class PlaintextExtractor(Extractor):
    name = "plaintext"
    binary = None

    def run(self, path, timeout=60):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return ExtractorResult(raw=f.read())
        except OSError as e:
            return ExtractorResult(error=str(e))
