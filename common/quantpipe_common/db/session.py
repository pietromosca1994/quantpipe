from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from quantpipe_common.config import DBConfig

# RLock, not Lock: get_session_factory()'s locked section calls get_engine(),
# which acquires this same lock — a plain Lock would self-deadlock there.
_lock = threading.RLock()
_default_engine: Engine | None = None
_default_session_factory: sessionmaker[Session] | None = None


def get_engine(config: DBConfig | None = None) -> Engine:
    """Build an engine for an explicit config; reuse one cached engine for the
    process-default config (no config passed) so pooling stays consistent
    across ingestion/training/inference call sites that don't pass one.
    """
    if config is not None:
        return create_engine(config.sqlalchemy_dsn, pool_pre_ping=True)

    global _default_engine
    if _default_engine is None:
        with _lock:
            if _default_engine is None:
                _default_engine = create_engine(DBConfig().sqlalchemy_dsn, pool_pre_ping=True)
    return _default_engine


def get_session_factory(config: DBConfig | None = None) -> sessionmaker[Session]:
    if config is not None:
        return sessionmaker(bind=get_engine(config), expire_on_commit=False)

    global _default_session_factory
    if _default_session_factory is None:
        with _lock:
            if _default_session_factory is None:
                _default_session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _default_session_factory


@contextmanager
def session_scope(config: DBConfig | None = None) -> Iterator[Session]:
    """Transactional scope: commits on success, rolls back and re-raises on error."""
    session = get_session_factory(config)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
