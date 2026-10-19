import shutil
from dataclasses import dataclass


@dataclass
class ExtractorResult:
    raw: str | None = None
    error: str | None = None


class Extractor:
    """Base for text extraction from one local file. binary=None means pure
    Python, no subprocess/availability check needed."""

    name = "extractor"
    binary = None

    def available(self):
        return self.binary is None or shutil.which(self.binary) is not None

    def run(self, path, timeout=60):
        raise NotImplementedError
