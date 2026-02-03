"""
Migration: Add BSD Core tables (state + audit)

Run with:
  /home/ishai/code/Jewishcoach_azure/backend/venv/bin/python -m migrations.003_add_bsd_tables

Notes:
- If the DB doesn't exist, we create all tables from SQLAlchemy models.
- If the DB exists, we create BSD tables if missing.
"""

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()


def _db_exists(database_url: str) -> bool:
    if database_url.startswith("sqlite"):
        # Expected format: sqlite:///./coaching.db (relative) or sqlite:////abs/path
        if database_url.startswith("sqlite:////"):
            p = Path(database_url.replace("sqlite:////", "/"))
        else:
            p = Path(__file__).parent.parent / "coaching.db"
        return p.exists()
    return True  # For non-sqlite, assume managed by DB server


def upgrade():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./coaching.db")
    engine = create_engine(database_url)

    # If sqlite file missing: create all tables from models (fast path)
    if database_url.startswith("sqlite") and not _db_exists(database_url):
        print("DB file not found; creating schema from models...")
        from app.database import Base
        import app.models  # noqa: F401 (ensure models imported)

        Base.metadata.create_all(bind=engine)
        print("✅ Created schema from models")
        return

    with engine.connect() as conn:
        # BSD state table (one row per conversation)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bsd_session_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL UNIQUE,
                current_stage VARCHAR NOT NULL DEFAULT 'S0',
                cognitive_data JSON,
                metrics JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """))
        print("✓ Created bsd_session_states (if missing)")

        # BSD audit log table (many rows per conversation)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bsd_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                stage VARCHAR NOT NULL,
                decision VARCHAR NOT NULL,
                next_stage VARCHAR,
                reasons JSON,
                extracted JSON,
                raw_user_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """))
        print("✓ Created bsd_audit_logs (if missing)")

        conn.commit()
        print("\n✅ Migration completed successfully!")


def downgrade():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./coaching.db")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS bsd_audit_logs"))
        conn.execute(text("DROP TABLE IF EXISTS bsd_session_states"))
        conn.commit()
        print("✅ Downgrade completed!")


if __name__ == "__main__":
    print("🚀 Running BSD tables migration...")
    upgrade()




