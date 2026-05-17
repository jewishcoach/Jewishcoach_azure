#!/usr/bin/env python3
"""
Professional one-shot migration: SQLite → PostgreSQL for Jewish Coach backend tables.

What it does
------------
1. Ensures the target schema exists (``metadata.create_all``).
2. ``TRUNCATE … CASCADE`` on all ORM tables (destroys existing rows in Postgres).
3. Copies rows in foreign-key-safe order.
4. Aligns PostgreSQL sequences with ``MAX(id)`` where applicable.

Safety
------
* Requires ``CONFIRM_SQLITE_TO_PG_COPY=YES`` for mutating runs.
* Use ``--dry-run`` first: validates URLs, counts source rows, pings Postgres — no writes.

Example (after backups)
-----------------------
  cd backend
  export SOURCE_DATABASE_URL='sqlite:////absolute/path/coaching.db'
  export DATABASE_URL='postgresql+psycopg2://USER:PASS@HOST.postgres.database.azure.com:5432/DB?sslmode=require'
  PYTHONPATH=. python3 scripts/sqlite_to_postgres.py --dry-run
  export CONFIRM_SQLITE_TO_PG_COPY=YES
  PYTHONPATH=. python3 scripts/sqlite_to_postgres.py -v
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any


LOG = logging.getLogger("sqlite_to_postgres")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _validate_urls(src: str, dst: str) -> None:
    if not src or "sqlite" not in src.lower():
        raise SystemExit(
            "SOURCE_DATABASE_URL must be a SQLite URL, e.g. sqlite:////home/site/wwwroot/coaching.db"
        )
    if not dst or "postgres" not in dst.lower():
        raise SystemExit(
            "DATABASE_URL must be PostgreSQL, e.g. "
            "postgresql+psycopg2://user:pass@host:5432/dbname?sslmode=require"
        )


def _ping_postgres(dst: str) -> None:
    from sqlalchemy import create_engine, text

    e = create_engine(dst, pool_pre_ping=True)
    with e.connect() as conn:
        conn.execute(text("SELECT 1"))
    LOG.info("PostgreSQL connectivity check passed.")


def _source_row_counts(src: str, tables: list[Any]) -> dict[str, int]:
    from sqlalchemy import create_engine, func, select

    src_engine = create_engine(src, connect_args={"check_same_thread": False})
    out: dict[str, int] = {}
    with src_engine.connect() as conn:
        for t in tables:
            n = conn.execute(select(func.count()).select_from(t)).scalar_one()
            out[t.name] = int(n)
    return out


def run_dry_run(src: str, dst: str) -> int:
    os.environ["DATABASE_URL"] = dst
    from app.database import Base
    import app.models  # noqa: F401

    tables = list(Base.metadata.sorted_tables)
    LOG.info("ORM tables (FK order): %s", " → ".join(t.name for t in tables))
    _ping_postgres(dst)
    counts = _source_row_counts(src, tables)
    total = sum(counts.values())
    LOG.info("Source row counts (%s tables, %s rows total):", len(counts), total)
    for name in sorted(counts.keys()):
        LOG.info("  %-40s %8d", name, counts[name])
    LOG.info("Dry-run complete — no changes were made.")
    return 0


def run_copy(src: str, dst: str) -> int:
    if os.getenv("CONFIRM_SQLITE_TO_PG_COPY") != "YES":
        raise SystemExit(
            "Refusing destructive copy: set CONFIRM_SQLITE_TO_PG_COPY=YES "
            "(after backup). Or use --dry-run to inspect only."
        )

    os.environ["DATABASE_URL"] = dst

    from sqlalchemy import create_engine, insert, select, text

    from app.database import Base, engine as dst_engine
    import app.models  # noqa: F401

    src_engine = create_engine(src, connect_args={"check_same_thread": False})
    tables = list(Base.metadata.sorted_tables)

    LOG.info("Creating tables on PostgreSQL if missing …")
    Base.metadata.create_all(dst_engine)

    names = ", ".join(f'"{t.name}"' for t in tables)
    LOG.warning("Truncating ALL application tables on PostgreSQL (%d tables) …", len(tables))
    with dst_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))

    LOG.info("Copying rows from SQLite …")
    grand_total = 0
    with src_engine.connect() as sc, dst_engine.begin() as dc:
        for t in tables:
            rows = sc.execute(select(t)).mappings().all()
            if not rows:
                LOG.debug("%s: 0 rows (skip)", t.name)
                continue
            payload = [dict(r) for r in rows]
            dc.execute(insert(t), payload)
            grand_total += len(payload)
            LOG.info("%s: copied %d rows", t.name, len(payload))

    LOG.info("Adjusting sequences …")
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

    LOG.info("Finished. Total rows inserted: %d", grand_total)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy Jewish Coach ORM tables from SQLite to PostgreSQL.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate connectivity and print source row counts; no writes.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Debug logging.",
    )
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)

    src = os.getenv("SOURCE_DATABASE_URL", "").strip()
    dst = os.getenv("DATABASE_URL", "").strip()
    _validate_urls(src, dst)

    try:
        if args.dry_run:
            return run_dry_run(src, dst)
        return run_copy(src, dst)
    except Exception:
        LOG.exception("Migration failed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
