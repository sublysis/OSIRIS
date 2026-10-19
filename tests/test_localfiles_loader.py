import os

import pytest

from osint.localfiles.loader import LocalFileLoader, PathTraversalError, resolve_case_path


def _make_case(tmp_path):
    case_dir = tmp_path / "case1"
    (case_dir / "uploads").mkdir(parents=True)
    return str(case_dir)


def test_resolve_case_path_accepts_file_inside_uploads(tmp_path):
    case_dir = _make_case(tmp_path)
    (tmp_path / "case1" / "uploads" / "doc.txt").write_text("x")
    resolved = resolve_case_path(case_dir, "doc.txt")
    assert resolved == os.path.realpath(os.path.join(case_dir, "uploads", "doc.txt"))


def test_resolve_case_path_rejects_parent_traversal(tmp_path):
    case_dir = _make_case(tmp_path)
    with pytest.raises(PathTraversalError):
        resolve_case_path(case_dir, "../../etc/passwd")


def test_resolve_case_path_rejects_absolute_escape(tmp_path):
    case_dir = _make_case(tmp_path)
    with pytest.raises(PathTraversalError):
        resolve_case_path(case_dir, "/etc/passwd")


def test_resolve_case_path_rejects_other_drive_escape(tmp_path):
    case_dir = _make_case(tmp_path)
    base_drive = os.path.splitdrive(os.path.realpath(case_dir))[0] or "C:"
    other_drive = "D:" if base_drive.upper() != "D:" else "C:"
    with pytest.raises(PathTraversalError):
        resolve_case_path(case_dir, other_drive + "/Windows/system32")


def test_resolve_case_path_rejects_sibling_prefix(tmp_path):
    case_dir = _make_case(tmp_path)
    (tmp_path / "case1" / "uploads_evil").mkdir()
    with pytest.raises(PathTraversalError):
        resolve_case_path(case_dir, "../uploads_evil/x.txt")


def test_resolve_case_path_rejects_ads_stream(tmp_path):
    case_dir = _make_case(tmp_path)
    with pytest.raises(PathTraversalError):
        resolve_case_path(case_dir, "note.txt::$DATA")


def test_resolve_case_path_rejects_trailing_dot_space(tmp_path):
    case_dir = _make_case(tmp_path)
    with pytest.raises(PathTraversalError):
        resolve_case_path(case_dir, "note. ")


def test_loader_extracts_plaintext(tmp_path, minimal_config):
    case_dir = _make_case(tmp_path)
    (tmp_path / "case1" / "uploads" / "note.txt").write_text("stylometry sample text", encoding="utf-8")
    result = LocalFileLoader(minimal_config).load(case_dir, "note.txt")
    assert result.ok is True
    assert result.text == "stylometry sample text"
    assert result.title == "note.txt"


def test_loader_reports_missing_file(tmp_path, minimal_config):
    case_dir = _make_case(tmp_path)
    result = LocalFileLoader(minimal_config).load(case_dir, "missing.txt")
    assert result.ok is False
    assert "not found" in result.error


def test_loader_rejects_traversal(tmp_path, minimal_config):
    case_dir = _make_case(tmp_path)
    result = LocalFileLoader(minimal_config).load(case_dir, "../outside.txt")
    assert result.ok is False
    assert "escapes" in result.error


def test_loader_enforces_max_bytes(tmp_path, minimal_config):
    case_dir = _make_case(tmp_path)
    (tmp_path / "case1" / "uploads" / "big.txt").write_bytes(b"x" * 100)
    minimal_config["localfiles"]["max_bytes"] = 10
    result = LocalFileLoader(minimal_config).load(case_dir, "big.txt")
    assert result.ok is False
    assert "max_bytes" in result.error


def test_loader_reports_unavailable_extractor(tmp_path, minimal_config, monkeypatch):
    case_dir = _make_case(tmp_path)
    (tmp_path / "case1" / "uploads" / "scan.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr("shutil.which", lambda name: None)
    result = LocalFileLoader(minimal_config).load(case_dir, "scan.png")
    assert result.ok is False
    assert "not installed" in result.error
