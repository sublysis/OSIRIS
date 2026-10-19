"""Journalism-context safety gates for the session/MCP layer.

Enforced in osint/session/service.py before any stage that touches a
network or spawns a subprocess runs - never in osint/pipeline.py itself,
so the classic cli.py one-shot flow (which already implies informed,
explicit flag usage) is unaffected.
"""

from osint.session import store

# INVARIANT: every stage dispatchable by osint/session/service.py must be
# classified here as network/subprocess-touching, or it is implicitly treated
# as read-only (no confirmation required). When service.py adds a new
# dispatchable stage, it MUST be added here if it touches a network or spawns a
# subprocess.
NETWORK_STAGES = frozenset({"fetch", "localfiles", "whois", "certs", "search"})
PAID_PROVIDERS = frozenset({"brave", "serpapi"})


class ConfirmationRequired(Exception):
    def __init__(self, message, stage):
        super().__init__(message)
        self.stage = stage


class BudgetExceeded(Exception):
    def __init__(self, message, provider, limit, used):
        super().__init__(message)
        self.provider = provider
        self.limit = limit
        self.used = used


def require_confirmation(stage, confirm):
    if stage in NETWORK_STAGES and not confirm:
        raise ConfirmationRequired(
            f"stage '{stage}' touches external systems/subprocesses - call again with confirm=True "
            "only after the journalist has explicitly approved this pivot",
            stage=stage,
        )


def check_search_budget(case_dir, provider, config):
    if provider not in PAID_PROVIDERS:
        return
    limit = (config.get("guardrails", {}) or {}).get("max_paid_search_calls_per_case", 20)
    used = store.count_audit_actions(case_dir, action=f"search:{provider}")
    if used >= limit:
        raise BudgetExceeded(
            f"{provider} call budget ({limit}) exhausted for this case",
            provider=provider,
            limit=limit,
            used=used,
        )
