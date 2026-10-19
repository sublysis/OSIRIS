import os

from osint.session import store


def test_init_case_creates_sqlite_file(tmp_path):
    case_dir = str(tmp_path / "case1")
    store.init_case(case_dir, case_id="case1", name="Operation Foo")
    assert os.path.exists(os.path.join(case_dir, "case.sqlite"))


def test_add_and_list_artifacts(tmp_path):
    case_dir = str(tmp_path / "case1")
    store.init_case(case_dir, "case1", "Operation Foo")
    artifact_id = store.add_artifact(case_dir, "url", "https://example.com", "https://example.com", added_via="agent")
    artifacts = store.list_artifacts(case_dir)
    assert len(artifacts) == 1
    assert artifacts[0]["id"] == artifact_id
    assert artifacts[0]["type"] == "url"
    assert artifacts[0]["value"] == "https://example.com"


def test_add_artifact_is_idempotent_on_type_value(tmp_path):
    case_dir = str(tmp_path / "case1")
    store.init_case(case_dir, "case1", "Operation Foo")
    id1 = store.add_artifact(case_dir, "url", "https://example.com", "https://example.com", "agent")
    id2 = store.add_artifact(case_dir, "url", "https://example.com", "https://example.com", "agent")
    assert id1 == id2
    assert len(store.list_artifacts(case_dir)) == 1


def test_save_and_get_stage_result(tmp_path):
    case_dir = str(tmp_path / "case1")
    store.init_case(case_dir, "case1", "Operation Foo")
    artifact_id = store.add_artifact(case_dir, "url", "https://example.com", "https://example.com", "agent")
    store.save_stage_result(case_dir, artifact_id, "fetch", {"text": "hello", "chars": 5})
    result = store.get_stage_result(case_dir, artifact_id, "fetch")
    assert result == {"text": "hello", "chars": 5}


def test_get_stage_result_returns_none_when_missing(tmp_path):
    case_dir = str(tmp_path / "case1")
    store.init_case(case_dir, "case1", "Operation Foo")
    artifact_id = store.add_artifact(case_dir, "url", "https://example.com", "https://example.com", "agent")
    assert store.get_stage_result(case_dir, artifact_id, "whois") is None


def test_save_links_replaces_previous_links(tmp_path):
    case_dir = str(tmp_path / "case1")
    store.init_case(case_dir, "case1", "Operation Foo")
    store.save_links(case_dir, [{"a": "x", "b": "y", "score": 0.8, "evidence": [{"kind": "stylometry", "detail": "d", "weight": 0.5}]}])
    store.save_links(case_dir, [{"a": "x", "b": "z", "score": 0.5, "evidence": []}])
    links = store.get_links(case_dir)
    assert len(links) == 1
    assert links[0]["b"] == "z"


def test_append_and_get_audit_log(tmp_path):
    case_dir = str(tmp_path / "case1")
    store.init_case(case_dir, "case1", "Operation Foo")
    store.append_audit(case_dir, actor="journalist", action="run_stage:fetch", detail="confirmed pivot", confirmed=True)
    log = store.get_audit_log(case_dir)
    assert len(log) == 1
    assert log[0]["action"] == "run_stage:fetch"
    assert log[0]["confirmed"] is True


def test_count_audit_actions(tmp_path):
    case_dir = str(tmp_path / "case1")
    store.init_case(case_dir, "case1", "Operation Foo")
    store.append_audit(case_dir, "agent", "search:brave", "q1", True)
    store.append_audit(case_dir, "agent", "search:brave", "q2", True)
    store.append_audit(case_dir, "agent", "search:searxng", "q3", True)
    assert store.count_audit_actions(case_dir, "search:brave") == 2
