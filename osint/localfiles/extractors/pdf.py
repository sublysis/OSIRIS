import subprocess

from .base import Extractor, ExtractorResult


class PdfExtractor(Extractor):
    name = "pdftotext"
    binary = "pdftotext"

    def run(self, path, timeout=60):
        try:
            proc = subprocess.run(
                [self.binary, path, "-"],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ExtractorResult(error="pdftotext timeout")
        except OSError as e:
            return ExtractorResult(error=str(e))
        if proc.returncode != 0:
            return ExtractorResult(error=proc.stderr.strip() or f"pdftotext exit {proc.returncode}")
        return ExtractorResult(raw=proc.stdout)
