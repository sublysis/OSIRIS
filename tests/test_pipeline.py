from unittest.mock import patch

from osint import pipeline
from osint.fetcher.fetch import FetchResult
from osint.input_parser.classifier import Artifact, ArtifactType
from osint.localfiles.loader import LocalFileResult


def test_fetch_urls_writes_text_into_matching_result_entry():
    art = Artifact(ArtifactType.URL, "https://example.com", "https://example.com")
    results = [{"type": "url", "value": "https://example.com", "raw": art.raw}]

    with patch("osint.pipeline.Fetcher") as MockFetcher:
        MockFetcher.return_value.fetch.return_value = FetchResult(
            "https://example.com", True, status=200, title="Example", text="hello world",
        )
        outcomes = pipeline.fetch_urls([art], {}, results)

    assert results[0]["text"] == "hello world"
    assert results[0]["title"] == "Example"
    assert results[0]["chars"] == 11
    assert outcomes == [{"value": "https://example.com", "ok": True, "status": 200, "chars": 11}]


def test_fetch_urls_records_error_on_failure():
    art = Artifact(ArtifactType.URL, "https://example.com", "https://example.com")
    results = [{"type": "url", "value": "https://example.com", "raw": art.raw}]

    with patch("osint.pipeline.Fetcher") as MockFetcher:
        MockFetcher.return_value.fetch.return_value = FetchResult(
            "https://example.com", False, status=404, error="HTTP 404",
        )
        outcomes = pipeline.fetch_urls([art], {}, results)

    assert results[0]["error"] == "HTTP 404"
    assert outcomes == [{"value": "https://example.com", "ok": False, "error": "HTTP 404"}]


def test_fetch_urls_noop_on_empty_list():
    assert pipeline.fetch_urls([], {}, []) == []


def test_load_local_files_writes_text_into_matching_result_entry(tmp_path):
    (tmp_path / "uploads").mkdir()
    (tmp_path / "uploads" / "doc.txt").write_text("leaked memo text", encoding="utf-8")
    art = Artifact(ArtifactType.FILE, "doc.txt", "file:doc.txt")
    results = [{"type": "file", "value": "doc.txt", "raw": art.raw}]

    outcomes = pipeline.load_local_files([art], str(tmp_path), {}, results)

    assert results[0]["text"] == "leaked memo text"
    assert results[0]["title"] == "doc.txt"
    assert outcomes[0]["ok"] is True


def test_load_local_files_noop_on_empty_list():
    assert pipeline.load_local_files([], "/irrelevant", {}, []) == []
