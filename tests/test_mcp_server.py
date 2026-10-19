import importlib

import pytest


@pytest.fixture
def mcp_module(tmp_path, monkeypatch):
    module = importlib.import_module("mcp_server")
    monkeypatch.setattr(module, "CASES_ROOT", str(tmp_path))
    return module


def test_create_case_tool_returns_case_id(mcp_module):
    result = mcp_module.create_case("Operation Foo")
    assert "case_id" in result
    assert "case_dir" in result


def test_add_artifact_tool_roundtrip(mcp_module):
    created = mcp_module.create_case("Operation Foo")
    result = mcp_module.add_artifact(created["case_id"], "url", "https://example.com")
    assert result["type"] == "url"


def test_run_stage_tool_blocks_without_confirm(mcp_module):
    created = mcp_module.create_case("Operation Foo")
    mcp_module.add_artifact(created["case_id"], "url", "https://example.com")
    with pytest.raises(Exception):
        mcp_module.run_stage(created["case_id"], "fetch", confirm=False)


def test_get_state_tool_returns_artifacts(mcp_module):
    created = mcp_module.create_case("Operation Foo")
    mcp_module.add_artifact(created["case_id"], "url", "https://example.com")
    state = mcp_module.get_state(created["case_id"])
    assert len(state["artifacts"]) == 1


def test_get_audit_log_tool_returns_list(mcp_module):
    created = mcp_module.create_case("Operation Foo")
    log = mcp_module.get_audit_log(created["case_id"])
    assert log == []
