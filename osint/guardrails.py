"""Journalism-context safety gates for the session/MCP layer.

Enforced in osint/session/service.py before any stage that touches a
network or spawns a subprocess runs - never in osint/pipeline.py itself,
so the classic cli.py one-shot flow (which already implies informed,
explicit flag usage) is unaffected.
"""

from osint.session import store

NETWORK_STAGES = {"fetch", "localfiles", "whois", "certs", "search"}
PAID_PROVIDERS = {"brave", "serpapi"}


class ConfirmationRequired(Exception):
    pass


class BudgetExceeded(Exception):
    pass


def require_confirmation(stage, confirm):
    if stage in NETWORK_STAGES and not confirm:
        raise ConfirmationRequired(
            f"stage '{stage}' touches external systems/subprocesses - call again with confirm=True "
            "only after the journalist has explicitly approved this pivot"
        )


def check_search_budget(case_dir, provider, config):
    if provider not in PAID_PROVIDERS:
        return
    limit = (config.get("guardrails", {}) or {}).get("max_paid_search_calls_per_case", 20)
    used = store.count_audit_actions(case_dir, action=f"search:{provider}")
    if used >= limit:
        raise BudgetExceeded(f"{provider} call budget ({limit}) exhausted for this case")
