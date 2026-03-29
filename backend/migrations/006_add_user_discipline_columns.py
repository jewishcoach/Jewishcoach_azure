"""
Migration: Add primary_discipline, mentor_disciplines to users (SQLite / prod parity)
Run: cd backend && python migrations/006_add_user_discipline_columns.py
"""
from sqlalchemy import create_engine, text, inspect as sa_inspect
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./coaching.db")
engine = create_engine(DATABASE_URL)


def upgrade():
    insp = sa_inspect(engine)
    with engine.connect() as conn:
        cols = [c["name"] for c in insp.get_columns("users")]
        if "primary_discipline" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN primary_discipline VARCHAR"))
            conn.commit()
            print("✓ Added primary_discipline to users")
        else:
            print("✓ primary_discipline already present")
        cols = [c["name"] for c in insp.get_columns("users")]
        if "mentor_disciplines" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN mentor_disciplines TEXT"))
            conn.commit()
            print("✓ Added mentor_disciplines to users")
        else:
            print("✓ mentor_disciplines already present")
    print("✅ Migration 006 done")


if __name__ == "__main__":
    upgrade()
