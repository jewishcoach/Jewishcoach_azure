#!/usr/bin/env python3
"""
Copy all application tables from SQLite → PostgreSQL.

- Empties target Postgres tables (TRUNCATE … CASCADE, RESTART IDENTITY).
- Inserts rows in FK-safe order (SQLAlchemy sorted_tables).
- Resets SERIAL sequences to MAX(id).

Run from repo backend/ with PYTHONPATH including the app root, e.g.:

  cd backend
  export SOURCE_DATABASE_URL='sqlite:////abs/path/coaching.db'
  export DATABASE_URL='postgresql+psycopg2://USER:PASS@HOST:5432/DB?sslmode=require'
  export CONFIRM_SQLITE_TO_PG_COPY=YES
  PYTHONPATH=. python3 scripts/sqlite_to_postgres.py
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    src = os.getenv("SOURCE_DATABASE_URL", "").strip()
    dst = os.getenv("DATABASE_URL", "").strip()
    if not src or "sqlite" not in src.lower():
        print(
            "SOURCE_DATABASE_URL must be SQLite, e.g. sqlite:////home/site/wwwroot/coaching.db",
            file=sys.stderr,
        )
        return 1
    if not dst or "postgres" not in dst.lower():
        print(
            "DATABASE_URL must be PostgreSQL, e.g. postgresql+psycopg2://user:pass@host:5432/db?sslmode=require",
            file=sys.stderr,
        )
        return 1
    if os.getenv("CONFIRM_SQLITE_TO_PG_COPY") != "YES":
        print("Refusing: set CONFIRM_SQLITE_TO_PG_COPY=YES", file=sys.stderr)
        return 1

    os.environ["DATABASE_URL"] = dst

    from sqlalchemy import create_engine, select, text

    from app.database import Base, engine as dst_engine
    import app.models  # noqa: F401 — register metadata tables

    src_engine = create_engine(src, connect_args={"check_same_thread": False})

    tables = list(Base.metadata.sorted_tables)
    Base.metadata.create_all(dst_engine)

    names = ", ".join(f'"{t.name}"' for t in tables)
    with dst_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))

    with src_engine.connect() as sc, dst_engine.begin() as dc:
        for t in tables:
            rows = sc.execute(select(t)).mappings().all()
            for row in rows:
                dc.execute(t.insert().values(**dict(row)))

    with dst_engine.begin() as conn:
        for t in tables:
            pk_cols = list(t.primary_key.columns)
            if len(pk_cols) != 1:
                continue
            col = pk_cols[0].name
            tbl = t.name
            seq = conn.execute(
                text("SELECT pg_get_serial_sequence(:tbl, :col)"),
                {"tbl": tbl, "col": col},
            ).scalar()
            if not seq:
                continue
            stmt = text(
                'SELECT setval(:seq, COALESCE((SELECT MAX("' + col + '") FROM "' + tbl + '"), 1))'
            )
            conn.execute(stmt, {"seq": seq})

    print("Done: SQLite → PostgreSQL copy finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
