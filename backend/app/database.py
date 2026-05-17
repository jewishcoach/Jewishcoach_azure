from datetime import datetime, timezone
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./coaching.db")
_IS_SQLITE = "sqlite" in DATABASE_URL.lower()


def _engine_kwargs() -> dict:
    if _IS_SQLITE:
        return {
            "connect_args": {
                "check_same_thread": False,
                # Reduce "database is locked" under concurrent requests (Azure logs showed this under burst PATCH + POST).
                "timeout": float(os.getenv("SQLITE_BUSY_TIMEOUT_SEC", "30")),
            },
        }
    # PostgreSQL / other servers: pooling + reconnect after idle disconnect (Azure Flexible Server, etc.)
    return {
        "pool_pre_ping": True,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SEC", "280")),
    }


engine = create_engine(DATABASE_URL, **_engine_kwargs())


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record):
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
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
