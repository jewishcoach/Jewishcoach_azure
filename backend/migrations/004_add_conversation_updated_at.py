"""
Migration: Add updated_at to conversations table

The Conversation model was missing an updated_at column, causing a silent
error in get_conversation_insights_safe that was caught but logged as an
exception. This migration adds the column with a nullable constraint so
existing rows are valid (NULL = never explicitly updated).

Run with:
  python -m migrations.004_add_conversation_updated_at
"""

from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import os

load_dotenv()


def upgrade():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./coaching.db")
    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check if the column already exists (safe for re-running)
        inspector = inspect(engine)
        existing_cols = [c["name"] for c in inspector.get_columns("conversations")]

        if "updated_at" in existing_cols:
            print("✓ updated_at already exists, skipping")
        else:
            conn.execute(text(
                "ALTER TABLE conversations ADD COLUMN updated_at TIMESTAMP"
            ))
            conn.commit()
            print("✓ Added updated_at column to conversations")

    print("✅ Migration 004 completed!")


def downgrade():
    # SQLite doesn't support DROP COLUMN on old versions — skip
    print("⚠️  Downgrade not supported for this migration (SQLite limitation)")


if __name__ == "__main__":
    print("🚀 Running migration 004: add conversation.updated_at...")
    upgrade()
