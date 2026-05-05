"""
Ensure promotional coupons exist after deploy (idempotent).

Runs once per process at API startup so Postgres/SQLite DBs do not rely on
SQLite-only INSERT OR IGNORE in legacy migrations.
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from ..models import Coupon, CouponRedemption

logger = logging.getLogger(__name__)

BSD100_DESCRIPTION = (
    "BSD Special Launch Offer — lifetime Premium access (unlimited messages catalog tier)"
)


def _maybe_create_coupon_tables() -> bool:
    """Create coupons / coupon_redemptions if metadata drift left them missing."""
    try:
        from ..database import engine, Base

        Base.metadata.create_all(
            bind=engine,
            tables=[Coupon.__table__, CouponRedemption.__table__],
            checkfirst=True,
        )
        return True
    except Exception as ex:
        logger.warning("Could not create coupon tables via metadata: %s", ex)
        return False


def ensure_bsd100_coupon(db: Session, *, _ddl_retry: bool = False) -> None:
    """
    Guarantee BSD100 exists, grants premium, is active.

    Safe under multi-worker Gunicorn: duplicate inserts raise IntegrityError → rollback.
    If `coupons` is missing, attempts SQLAlchemy DDL once then retries.
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
        if _ddl_retry:
            logger.warning("BSD100 bootstrap failed after DDL retry: %s", e)
            return
        logger.warning("BSD100 bootstrap DB error (will try DDL once): %s", e)
        if _maybe_create_coupon_tables():
            ensure_bsd100_coupon(db, _ddl_retry=True)
