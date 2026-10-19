import subprocess

from osint.localfiles.extractors.ocr import OcrExtractor
from osint.localfiles.extractors.pdf import PdfExtractor
from osint.localfiles.extractors.plaintext import PlaintextExtractor


def test_plaintext_extractor_is_always_available():
    assert PlaintextExtractor().available() is True


def test_plaintext_extractor_reads_file(tmp_path):
    p = tmp_path / "note.txt"
    p.write_text("hello world", encoding="utf-8")
    result = PlaintextExtractor().run(str(p))
    assert result.error is None
    assert result.raw == "hello world"


def test_pdf_extractor_unavailable_when_binary_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert PdfExtractor().available() is False


def test_pdf_extractor_runs_pdftotext(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pdftotext")

    def fake_run(cmd, capture_output, text, timeout):
        assert cmd[0] == "pdftotext"
        assert cmd[-1] == "-"
        return subprocess.CompletedProcess(cmd, 0, stdout="extracted pdf text", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = PdfExtractor().run(str(tmp_path / "doc.pdf"))
    assert result.raw == "extracted pdf text"
    assert result.error is None


def test_pdf_extractor_reports_nonzero_exit(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pdftotext")

    def fake_run(cmd, capture_output, text, timeout):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="malformed PDF")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = PdfExtractor().run(str(tmp_path / "doc.pdf"))
    assert result.raw is None
    assert "malformed PDF" in result.error


def test_pdf_extractor_times_out(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pdftotext")

    def fake_run(cmd, capture_output, text, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = PdfExtractor().run(str(tmp_path / "doc.pdf"), timeout=1)
    assert result.error == "pdftotext timeout"


def test_pdf_extractor_reports_not_installed_without_calling_subprocess(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: None)

    def fail_run(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called when binary is missing")

    monkeypatch.setattr(subprocess, "run", fail_run)
    result = PdfExtractor().run(str(tmp_path / "doc.pdf"))
    assert result.raw is None
    assert "not installed" in result.error


def test_ocr_extractor_runs_tesseract(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/tesseract")

    def fake_run(cmd, capture_output, text, timeout):
        assert cmd[0] == "tesseract"
        assert cmd[-1] == "stdout"
        return subprocess.CompletedProcess(cmd, 0, stdout="ocr text", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = OcrExtractor().run(str(tmp_path / "scan.png"))
    assert result.raw == "ocr text"
    assert result.error is None


def test_ocr_extractor_reports_nonzero_exit(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/tesseract")

    def fake_run(cmd, capture_output, text, timeout):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="image not readable")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = OcrExtractor().run(str(tmp_path / "scan.png"))
    assert result.raw is None
    assert "image not readable" in result.error


def test_ocr_extractor_times_out(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/tesseract")

    def fake_run(cmd, capture_output, text, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = OcrExtractor().run(str(tmp_path / "scan.png"), timeout=1)
    assert result.error == "tesseract timeout"


def test_ocr_extractor_reports_not_installed_without_calling_subprocess(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: None)

    def fail_run(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called when binary is missing")

    monkeypatch.setattr(subprocess, "run", fail_run)
    result = OcrExtractor().run(str(tmp_path / "scan.png"))
    assert result.raw is None
    assert "not installed" in result.error
