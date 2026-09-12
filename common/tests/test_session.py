from unittest.mock import MagicMock

import pytest
from quantpipe_common.config import DBConfig
from quantpipe_common.db import session as session_module
from quantpipe_common.db.session import get_engine, get_session_factory, session_scope


@pytest.fixture(autouse=True)
def _reset_default_engine_cache():
    """Each test starts with no cached default engine/session factory."""
    session_module._default_engine = None
    session_module._default_session_factory = None
    yield
    session_module._default_engine = None
    session_module._default_session_factory = None


@pytest.fixture
def db_env(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "quantpipe")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_DB", "quantpipe")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")


def test_get_engine_caches_a_single_default_engine(db_env):
    first = get_engine()
    second = get_engine()

    assert first is second


def test_get_engine_builds_a_fresh_engine_for_an_explicit_config(db_env):
    default_engine = get_engine()
    explicit_config = DBConfig(
        user="other", password="pw", db="other_db", host="otherhost", port=5433
    )

    explicit_engine = get_engine(explicit_config)

    assert explicit_engine is not default_engine
    assert "otherhost" in str(explicit_engine.url)


def test_get_engine_never_lets_an_explicit_config_overwrite_the_default_cache(db_env):
    explicit_config = DBConfig(
        user="other", password="pw", db="other_db", host="otherhost", port=5433
    )
    get_engine(explicit_config)

    default_engine = get_engine()

    assert "localhost" in str(default_engine.url)


@pytest.mark.timeout(5)
def test_get_session_factory_does_not_deadlock_building_the_default_engine(db_env):
    """Regression test: get_session_factory()'s locked section calls
    get_engine(), which acquires the same lock — this must not self-deadlock.
    """
    factory = get_session_factory()

    assert factory is get_session_factory()


def test_session_scope_commits_on_success(monkeypatch):
    mock_session = MagicMock()
    monkeypatch.setattr(
        session_module, "get_session_factory", lambda config=None: lambda: mock_session
    )

    with session_scope() as session:
        assert session is mock_session

    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()
    mock_session.close.assert_called_once()


def test_session_scope_rolls_back_and_reraises_on_error(monkeypatch):
    mock_session = MagicMock()
    monkeypatch.setattr(
        session_module, "get_session_factory", lambda config=None: lambda: mock_session
    )

    with pytest.raises(RuntimeError), session_scope():
        raise RuntimeError("boom")

    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()
