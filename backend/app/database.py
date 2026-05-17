from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./coaching.db")

_sqlite_connect_args = (
    {
        "check_same_thread": False,
        # Reduce "database is locked" under concurrent requests (Azure logs showed this under burst PATCH + POST).
        "timeout": float(os.getenv("SQLITE_BUSY_TIMEOUT_SEC", "30")),
    }
    if "sqlite" in DATABASE_URL
    else {}
)

# Create engine (async support can be added later)
engine = create_engine(
    DATABASE_URL,
    connect_args=_sqlite_connect_args,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record):
    if "sqlite" not in DATABASE_URL:
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




