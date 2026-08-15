"""Monitoring / timeline (module 7).

Compares the current run with the previous stored run of the same input
and returns new/gone targets and links. Builds on the runs stored in
SQLite (report.store).
"""

from osint.report.store import get_previous_run, get_runs

from .diff import diff_outputs

__all__ = ["compare_to_previous", "run_timeline", "diff_outputs"]


def _db_path(config):
    return (config.get("report", {}) or {}).get("db_path", "data/osint.sqlite")


def compare_to_previous(config, current_output, input_name, before_id=None):
    prev = get_previous_run(_db_path(config), input_name, before_id)
    if prev is None:
        return None
    prev_id, prev_data = prev
    diff = diff_outputs(prev_data, current_output)
    diff["previous_run_id"] = prev_id
    return diff


def run_timeline(config, input_name=None, limit=50):
    return get_runs(_db_path(config), input_name, limit)
