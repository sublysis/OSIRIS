import pytest


@pytest.fixture
def minimal_config():
    return {
        "localfiles": {"max_bytes": 20_000_000, "timeout": 60},
        "guardrails": {"max_paid_search_calls_per_case": 20},
        "report": {"db_path": "data/osint_test.sqlite", "output_dir": "reports_test"},
    }
