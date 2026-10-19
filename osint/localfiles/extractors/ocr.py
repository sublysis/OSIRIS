import subprocess

from .base import Extractor, ExtractorResult


class OcrExtractor(Extractor):
    name = "tesseract"
    binary = "tesseract"

    def run(self, path, timeout=60):
        try:
            proc = subprocess.run(
                [self.binary, path, "stdout"],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ExtractorResult(error="tesseract timeout")
        except OSError as e:
            return ExtractorResult(error=str(e))
        if proc.returncode != 0:
            return ExtractorResult(error=proc.stderr.strip() or f"tesseract exit {proc.returncode}")
        return ExtractorResult(raw=proc.stdout)
