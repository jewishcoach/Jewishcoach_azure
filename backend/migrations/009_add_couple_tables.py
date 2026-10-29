"""
Migration: couple_sessions + couple_members tables (couple process)
Run: cd backend && python migrations/009_add_couple_tables.py
(On deploy startup.sh's create_all creates them too.)
"""
from sqlalchemy import create_engine, inspect as sa_inspect
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./coaching.db")

from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401


def upgrade():
    engine = create_engine(DATABASE_URL)
    existing = set(sa_inspect(engine).get_table_names())
    for model in (app.models.CoupleSession, app.models.CoupleMember):
        name = model.__tablename__
        if name not in existing:
            Base.metadata.create_all(bind=engine, tables=[model.__table__])
            print(f"✓ Created {name}")
        else:
            print(f"✓ {name} already present")
    print("✅ Migration 009 done")


if __name__ == "__main__":
    upgrade()
