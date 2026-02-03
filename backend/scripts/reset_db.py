"""
Reset the local SQLite DB (destructive).

This project uses SQLite by default (backend/coaching.db). Since you explicitly
approved DB reset, this helper deletes the DB file and recreates tables from
SQLAlchemy models (including BSD core tables).

Usage:
  cd /home/ishai/code/Jewishcoach_azure/backend
  ./venv/bin/python scripts/reset_db.py
"""

from __future__ import annotations

from pathlib import Path


def main():
    backend_dir = Path(__file__).parent.parent
    db_path = backend_dir / "coaching.db"

    if db_path.exists():
        print(f"Deleting DB: {db_path}")
        db_path.unlink()
    else:
        print(f"DB not found (ok): {db_path}")

    print("Recreating schema from models...")
    from app.database import engine, Base
    import app.models  # noqa: F401 (import models)

    Base.metadata.create_all(bind=engine)
    print("✅ Done. New DB created.")


if __name__ == "__main__":
    main()




