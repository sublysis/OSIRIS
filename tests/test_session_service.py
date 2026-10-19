import os
from pathlib import Path

import pytest

from osint.guardrails import ConfirmationRequired
from osint.session import service, store


def test_create_case_creates_directory_and_uploads_subdir(tmp_path):
    case_id, case_dir = service.create_case(str(tmp_path), "Operation Foo")
    assert os.path.isdir(os.path.join(case_dir, "uploads"))
    assert os.path.exists(os.path.join(case_dir, "case.sqlite"))


def test_add_artifact_classifies_and_stores(tmp_path):
    _, case_dir = service.create_case(str(tmp_path), "Operation Foo")
    result = service.add_artifact(case_dir, "url", "https://example.com", added_via="agent")
    assert result["type"] == "url"
    assert result["value"] == "https://example.com"
    assert len(store.list_artifacts(case_dir)) == 1


def test_add_artifact_file_type_validates_upload_exists(tmp_path):
    _, case_dir = service.create_case(str(tmp_path), "Operation Foo")
    with pytest.raises(FileNotFoundError):
        service.add_artifact(case_dir, "file", "missing.pdf", added_via="agent")


def test_add_artifact_file_type_succeeds_when_uploaded(tmp_path):
    _, case_dir = service.create_case(str(tmp_path), "Operation Foo")
    Path(case_dir, "uploads", "memo.txt").write_text("x")
    result = service.add_artifact(case_dir, "file", "memo.txt", added_via="agent")
    assert result["type"] == "file"


def test_run_stage_requires_confirmation_for_fetch(tmp_path):
    _, case_dir = service.create_case(str(tmp_path), "Operation Foo")
    service.add_artifact(case_dir, "url", "https://example.com", added_via="agent")
    with pytest.raises(ConfirmationRequired):
        service.run_stage(case_dir, {}, "fetch", confirm=False)


def test_run_stage_logs_blocked_attempt_to_audit(tmp_path):
    _, case_dir = service.create_case(str(tmp_path), "Operation Foo")
    service.add_artifact(case_dir, "url", "https://example.com", added_via="agent")
    with pytest.raises(ConfirmationRequired):
        service.run_stage(case_dir, {}, "fetch", confirm=False)
    log = store.get_audit_log(case_dir)
    assert any(e["action"] == "run_stage:fetch" and e["confirmed"] is False for e in log)


def test_run_stage_unknown_stage_raises_valueerror_and_audits(tmp_path):
    _, case_dir = service.create_case(str(tmp_path), "Operation Foo")
    with pytest.raises(ValueError) as exc:
        service.run_stage(case_dir, {}, "nlp", confirm=True)
    assert "nlp" in str(exc.value)
    assert "available" in str(exc.value)
    log = store.get_audit_log(case_dir)
    assert any(e["action"] == "run_stage:nlp" and e["confirmed"] is False for e in log)


def test_run_stage_fetch_persists_stage_result(tmp_path, monkeypatch):
    _, case_dir = service.create_case(str(tmp_path), "Operation Foo")
    service.add_artifact(case_dir, "url", "https://example.com", added_via="agent")

    from osint import pipeline

    def fake_fetch_urls(url_artifacts, config, results):
        results[0]["text"] = "fetched text"
        results[0]["title"] = "T"
        return [{"value": "https://example.com", "ok": True, "status": 200, "chars": 12}]

    monkeypatch.setattr(pipeline, "fetch_urls", fake_fetch_urls)
    outcome = service.run_stage(case_dir, {}, "fetch", confirm=True)

    assert outcome["stage"] == "fetch"
    assert outcome["results"][0]["ok"] is True
    artifact_id = store.list_artifacts(case_dir)[0]["id"]
    assert store.get_stage_result(case_dir, artifact_id, "fetch")["text"] == "fetched text"


def test_get_state_returns_artifacts_and_links(tmp_path):
    _, case_dir = service.create_case(str(tmp_path), "Operation Foo")
    service.add_artifact(case_dir, "url", "https://example.com", added_via="agent")
    state = service.get_state(case_dir)
    assert len(state["artifacts"]) == 1
    assert state["correlation"] == {"targets": [], "links": []}


def test_dispatchable_stages_are_all_classified_as_network_in_guardrails():
    """Closes the fail-open gap flagged in Task 7's review: every stage key
    this service can actually dispatch via run_stage must be present in
    guardrails.NETWORK_STAGES, or a future stage could silently ship without
    requiring confirmation. This does NOT assert the reverse (that every
    guardrails.NETWORK_STAGES entry is dispatchable yet) - whois/certs/search
    are reserved there for a future task and are not a bug."""
    from osint import guardrails

    dispatchable_stages = set(service._STAGE_DISPATCH.keys())
    assert dispatchable_stages.issubset(guardrails.NETWORK_STAGES), (
        f"stage(s) {dispatchable_stages - guardrails.NETWORK_STAGES} are dispatchable via "
        "run_stage but missing from guardrails.NETWORK_STAGES - they would run without "
        "requiring confirm=True"
    )
