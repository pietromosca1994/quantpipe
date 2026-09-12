import pytest
from prefect.testing.utilities import prefect_test_harness


@pytest.fixture(autouse=True, scope="session")
def _prefect_test_fixture():
    """Run every test against Prefect's ephemeral test database instead of
    spawning a real local API server subprocess for each flow/task call.

    Session-scoped because the harness itself costs ~30-60s to set up (a real,
    if temporary, Prefect API + SQLite DB) — that cost is paid once per test
    run, not per test.
    """
    with prefect_test_harness():
        yield
