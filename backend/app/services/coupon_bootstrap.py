"""
Ensure promotional coupons exist after deploy (idempotent).

Runs once per process at API startup so Postgres/SQLite DBs do not rely on
SQLite-only INSERT OR IGNORE in legacy migrations.
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from ..models import Coupon

logger = logging.getLogger(__name__)

BSD100_DESCRIPTION = (
    "BSD Special Launch Offer — lifetime Premium access (unlimited messages catalog tier)"
)


def ensure_bsd100_coupon(db: Session) -> None:
    """
    Guarantee BSD100 exists, grants premium, is active.

    Safe under multi-worker Gunicorn: duplicate inserts raise IntegrityError → rollback.
    Missing `coupons` table → log and skip (migrations not applied yet).
    """
    try:
        existing = db.query(Coupon).filter(Coupon.code == "BSD100").first()
        if existing:
            changed = False
            if existing.plan_granted != "premium":
                existing.plan_granted = "premium"
                changed = True
            if not existing.is_active:
                existing.is_active = True
                changed = True
            if (existing.description or "") != BSD100_DESCRIPTION:
                existing.description = BSD100_DESCRIPTION
                changed = True
            if changed:
                db.commit()
                logger.info("BSD100 coupon aligned (plan/active/description)")
            return

        db.add(
            Coupon(
                code="BSD100",
                plan_granted="premium",
                duration_days=None,
                max_uses=None,
                current_uses=0,
                is_active=True,
                expires_at=None,
                description=BSD100_DESCRIPTION,
            )
        )
        db.commit()
        logger.info("BSD100 coupon created")
    except IntegrityError:
        db.rollback()
        logger.debug("BSD100 insert raced or duplicate; treating as ok")
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        logger.warning("BSD100 bootstrap skipped (coupons table missing or DB error): %s", e)
