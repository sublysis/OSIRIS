from .base import Extractor, ExtractorResult
from .ocr import OcrExtractor
from .pdf import PdfExtractor
from .plaintext import PlaintextExtractor

EXTRACTORS = {
    ".pdf": PdfExtractor(),
    ".txt": PlaintextExtractor(),
    ".md": PlaintextExtractor(),
    ".csv": PlaintextExtractor(),
    ".log": PlaintextExtractor(),
    ".png": OcrExtractor(),
    ".jpg": OcrExtractor(),
    ".jpeg": OcrExtractor(),
    ".tif": OcrExtractor(),
    ".tiff": OcrExtractor(),
}

__all__ = ["Extractor", "ExtractorResult", "EXTRACTORS", "PdfExtractor", "OcrExtractor", "PlaintextExtractor"]
