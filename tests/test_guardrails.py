import pytest

from osint import guardrails


def test_require_confirmation_blocks_network_stage_without_confirm():
    with pytest.raises(guardrails.ConfirmationRequired):
        guardrails.require_confirmation("fetch", confirm=False)


def test_require_confirmation_allows_network_stage_with_confirm():
    guardrails.require_confirmation("fetch", confirm=True)  # no raise


def test_require_confirmation_allows_read_only_stage_without_confirm():
    guardrails.require_confirmation("correlate", confirm=False)  # no raise


@pytest.mark.parametrize("stage", ["fetch", "localfiles", "whois", "certs", "search"])
def test_all_network_and_subprocess_stages_require_confirmation(stage):
    with pytest.raises(guardrails.ConfirmationRequired):
        guardrails.require_confirmation(stage, confirm=False)


def test_check_search_budget_ignores_free_provider(tmp_path):
    guardrails.check_search_budget(str(tmp_path), "searxng", {})  # no raise, no store needed


def test_check_search_budget_raises_when_exhausted(tmp_path, monkeypatch):
    from osint.session import store
    store.init_case(str(tmp_path), "case1", "test")
    config = {"guardrails": {"max_paid_search_calls_per_case": 2}}
    store.append_audit(str(tmp_path), "agent", "search:brave", "q1", True)
    store.append_audit(str(tmp_path), "agent", "search:brave", "q2", True)
    with pytest.raises(guardrails.BudgetExceeded):
        guardrails.check_search_budget(str(tmp_path), "brave", config)


def test_check_search_budget_allows_under_limit(tmp_path):
    from osint.session import store
    store.init_case(str(tmp_path), "case1", "test")
    config = {"guardrails": {"max_paid_search_calls_per_case": 2}}
    store.append_audit(str(tmp_path), "agent", "search:brave", "q1", True)
    guardrails.check_search_budget(str(tmp_path), "brave", config)  # no raise
