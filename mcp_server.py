#!/usr/bin/env python3
"""MCP server exposing the osint_stylometric_search pipeline as tools for
agentic/journalistic investigation workflows.

Thin wrapper only - no pipeline/session logic lives here, see
osint/session/service.py. Dispatchable stages that touch a network or spawn a
subprocess (currently fetch and localfiles) require confirm=True; whois, certs
and search are gated the same way but are reserved and not yet dispatchable.
Set confirm=True only after the journalist has explicitly approved the pivot -
i.e. the actual network fetch / subprocess spawn, third-party contact, and any
cost it may incur (see osint/guardrails.py).
"""

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from osint.config import load_config
from osint.guardrails import BudgetExceeded, ConfirmationRequired
from osint.report import generate as render_reports
from osint.session import service

mcp = MCPServer("osint-stylometric-search")
CASES_ROOT = "cases"


@mcp.tool()
def create_case(name: str) -> dict:
    """Create a new investigation case (own directory + SQLite session store + uploads/ folder)."""
    case_id, case_dir = service.create_case(CASES_ROOT, name)
    return {"case_id": case_id, "case_dir": case_dir}


@mcp.tool()
def add_artifact(case_id: str, type: str, value: str) -> dict:
    """Register a new artifact (url/email/username/name/file) in the case.
    For type=file, the file must already exist under <case_dir>/uploads/."""
    case_dir = service.resolve_case_dir(CASES_ROOT, case_id)
    return service.add_artifact(case_dir, type, value, added_via="mcp")


@mcp.tool()
def run_stage(case_id: str, stage: str, confirm: bool = False) -> dict:
    """Run one pipeline stage over the case's artifacts. Dispatchable now:
    fetch, localfiles (whois, certs, search are gated the same way but reserved
    and not yet dispatchable). These stages perform a real network fetch or
    spawn a subprocess, may contact third parties, and may incur cost, so they
    raise unless confirm=True - pass confirm=True only after the journalist has
    explicitly approved this specific pivot."""
    case_dir = service.resolve_case_dir(CASES_ROOT, case_id)
    config = load_config()
    try:
        return service.run_stage(case_dir, config, stage, confirm=confirm)
    except (ConfirmationRequired, ValueError, BudgetExceeded) as e:
        raise ToolError(str(e)) from e


@mcp.tool()
def get_state(case_id: str) -> dict:
    """Return all artifacts, stage results, and correlation links for the case."""
    case_dir = service.resolve_case_dir(CASES_ROOT, case_id)
    return service.get_state(case_dir)


@mcp.tool()
def generate_report(case_id: str, formats: str = "md,html") -> dict:
    """Render report files (md/html/graphml/maltego) from the case's current state.
    Note: the current get_state() does not merge fetched page text back into
    artifacts, so reports render thin/incomplete at this stage - this is an
    accepted limitation, not a signal to re-run fetch."""
    case_dir = service.resolve_case_dir(CASES_ROOT, case_id)
    config = load_config()
    state = service.get_state(case_dir)
    written = render_reports(state, config, case_id, formats.split(","), None, case_dir)
    return {"written": written}


@mcp.tool()
def get_audit_log(case_id: str) -> list:
    """Return the full audit trail (every tool call, confirmed or blocked) for the case - for sourcing/chain-of-custody."""
    case_dir = service.resolve_case_dir(CASES_ROOT, case_id)
    return service.get_audit_log(case_dir)


if __name__ == "__main__":
    mcp.run()
