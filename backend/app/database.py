"""
Database engine and session factory.

Supports:
  - SQLite (local dev / legacy App Service file DB): WAL + busy timeout to reduce lock contention.
  - PostgreSQL (recommended production): connection pool, pre-ping, recycle for Azure Flexible Server.

Configure via ``DATABASE_URL``. SQLAlchemy URL cheatsheet:

  SQLite file (relative path): ``sqlite:///./coaching.db``
  SQLite absolute path (four slashes): ``sqlite:////var/data/coaching.db``
  PostgreSQL (psycopg2): ``postgresql+psycopg2://user:pass@host:5432/dbname?sslmode=require``
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./coaching.db")
_IS_SQLITE = "sqlite" in DATABASE_URL.lower()


def _int_env(name: str, default: int, *, minimum: int | None = None) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        v = int(raw)
    except ValueError:
        return default
    if minimum is not None and v < minimum:
        return default
    return v


def _sqlite_engine_kwargs() -> dict:
    """
    SQLite uses SQLAlchemy's QueuePool by default (small pool). For parallel load tests,
    set SQLITE_POOL_SIZE / SQLITE_MAX_OVERFLOW to avoid pool timeouts.
    """
    out: dict = {
        "connect_args": {
            "check_same_thread": False,
            "timeout": float(os.getenv("SQLITE_BUSY_TIMEOUT_SEC", "30")),
        },
    }
    raw_pool = os.getenv("SQLITE_POOL_SIZE", "").strip()
    if raw_pool:
        try:
            ps = max(1, int(raw_pool))
            out["pool_size"] = ps
            out["max_overflow"] = _int_env("SQLITE_MAX_OVERFLOW", max(10, ps), minimum=0)
            out["pool_timeout"] = _int_env("SQLITE_POOL_TIMEOUT", 60, minimum=1)
        except ValueError:
            pass
    return out


def _postgres_engine_kwargs() -> dict:
    # Conservative defaults for Azure Flexible Server (B1ms ≈ 50 max_connections):
    # 2 Gunicorn workers × (pool_size + max_overflow) should stay well under the limit.
    return {
        "pool_pre_ping": True,
        "pool_size": _int_env("DB_POOL_SIZE", 3, minimum=1),
        "max_overflow": _int_env("DB_MAX_OVERFLOW", 5, minimum=0),
        "pool_timeout": _int_env("DB_POOL_TIMEOUT", 30, minimum=1),
        "pool_recycle": _int_env("DB_POOL_RECYCLE_SEC", 280, minimum=-1),
    }


def _engine_kwargs() -> dict:
    return _sqlite_engine_kwargs() if _IS_SQLITE else _postgres_engine_kwargs()


engine: Engine = create_engine(DATABASE_URL, **_engine_kwargs())


def is_sqlite_backend() -> bool:
    """Return True if the active URL targets SQLite."""
    return _IS_SQLITE


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record) -> None:
    if not _IS_SQLITE:
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        ms = int(float(os.getenv("SQLITE_BUSY_TIMEOUT_SEC", "30")) * 1000)
        cursor.execute(f"PRAGMA busy_timeout={ms}")
    finally:
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def utc_now():
    """Timezone-aware UTC now (replaces deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc)


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
