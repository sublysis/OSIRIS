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


def _url_art(value="https://example.com"):
    return Artifact(ArtifactType.URL, value, value)


def test_run_whois_writes_result_into_entry():
    art = _url_art()
    results = [{"type": "url", "value": art.value, "raw": art.raw}]

    with patch("osint.pipeline.WhoisClient") as MockClient, \
            patch("osint.pipeline.canonical_domain", return_value="example.com"):
        lookup = MockClient.return_value.lookup.return_value
        lookup.ok = True
        lookup.registrant_org = "Acme"
        lookup.registrant_email = None
        lookup.redacted = False
        lookup.registrar = "RegX"
        lookup.to_dict.return_value = {"registrar": "RegX"}
        outcomes = pipeline.run_whois([art], {}, results)

    assert results[0]["whois"] == {"registrar": "RegX"}
    assert outcomes == [{
        "value": art.value, "domain": "example.com", "ok": True,
        "registrar": "RegX", "note": "",
    }]


def test_run_whois_noop_on_empty_list():
    assert pipeline.run_whois([], {}, []) == []


def test_run_certs_writes_result_into_entry():
    art = _url_art()
    results = [{"type": "url", "value": art.value, "raw": art.raw}]

    with patch("osint.pipeline.CertClient") as MockClient, \
            patch("osint.pipeline.canonical_domain", return_value="example.com"):
        lookup = MockClient.return_value.lookup.return_value
        lookup.ok = True
        lookup.cert_count = 5
        lookup.subdomains = ["a.example.com", "b.example.com"]
        lookup.to_dict.return_value = {"cert_count": 5}
        outcomes = pipeline.run_certs([art], {}, results)

    assert results[0]["certs"] == {"cert_count": 5}
    assert outcomes == [{
        "value": art.value, "domain": "example.com", "ok": True,
        "cert_count": 5, "subdomains": 2,
    }]


def test_run_certs_noop_on_empty_list():
    assert pipeline.run_certs([], {}, []) == []


def test_run_nlp_no_texts_returns_none():
    results = [{"type": "url", "value": "https://example.com", "raw": ""}]
    stylometry, report = pipeline.run_nlp(results, {})
    assert stylometry is None
    assert report == {"docs": 0}


def test_run_nlp_single_doc_runs_entities_and_skips_stylometry():
    results = [{"type": "url", "value": "https://example.com", "raw": "", "text": "hello world"}]

    class _Ent:
        label, text = "PER", "x"

    with patch("osint.pipeline.EntityExtractor") as MockNer, \
            patch("osint.pipeline.KeyphraseExtractor") as MockKp, \
            patch("osint.pipeline.basic_features", return_value={"a": 1.23456}):
        MockNer.return_value.extract.return_value = [_Ent()]
        MockKp.return_value.extract.return_value = []
        stylometry, report = pipeline.run_nlp(results, {})

    assert report["docs"] == 1
    assert results[0]["entities"] == [{"label": "PER", "text": "x"}]
    assert results[0]["style"] == {"a": 1.23456}
    assert stylometry == []
    assert report["stylometry_skipped"] == "needs >=2 texts"


def test_run_search_noop_when_no_provider_and_no_tools():
    outcomes = pipeline.run_search({}, {}, [], None, 10)
    assert outcomes["web"] == []
    assert all(t["status"] == "noop" for t in outcomes["tools"])


def test_run_search_web_hits_written_into_entry():
    name_art = Artifact(ArtifactType.NAME, "Max Master", "Max Master")
    groups = {ArtifactType.NAME: [name_art]}
    results = [{"type": "name", "value": "Max Master", "raw": "Max Master"}]

    class _Hit:
        def to_dict(self):
            return {"url": "http://h"}

    with patch("osint.pipeline.get_provider") as MockGet, \
            patch("osint.pipeline.MaigretWrapper") as MockMaigret, \
            patch("osint.pipeline.HoleheWrapper") as MockHolehe:
        provider = MockGet.return_value
        provider.name = "searxng"
        provider.search.return_value = [_Hit()]
        MockMaigret.return_value.name = "maigret"
        MockMaigret.return_value.binary = "maigret"
        MockHolehe.return_value.name = "holehe"
        MockHolehe.return_value.binary = "holehe"
        outcomes = pipeline.run_search(groups, {}, results, None, 10)

    assert results[0]["search"] == [{"url": "http://h"}]
    assert outcomes["provider_name"] == "searxng"
    assert outcomes["web"] == [{"value": "Max Master", "hits": 1}]


def test_run_correlate_delegates():
    with patch("osint.pipeline.correlate", return_value="CORR") as mock_corr:
        assert pipeline.run_correlate([{"a": 1}], None, {}) == "CORR"
        mock_corr.assert_called_once_with([{"a": 1}], None, {})


def test_run_monitor_delegates():
    with patch("osint.pipeline.compare_to_previous", return_value="DIFF") as mock_cmp:
        assert pipeline.run_monitor({}, {"out": 1}, "input.txt") == "DIFF"
        mock_cmp.assert_called_once_with({}, {"out": 1}, "input.txt")
