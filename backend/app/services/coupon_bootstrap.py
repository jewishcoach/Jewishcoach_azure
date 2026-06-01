"""
Ensure promotional coupons exist after deploy (idempotent).

Runs once per process at API startup so Postgres/SQLite DBs do not rely on
SQLite-only INSERT OR IGNORE in legacy migrations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from ..models import Coupon, CouponRedemption

logger = logging.getLogger(__name__)

BSD100_DESCRIPTION = (
    "BSD Special Launch Offer — lifetime Premium access (unlimited messages catalog tier)"
)
SHELA000_DESCRIPTION = (
    "Shela offer — lifetime Premium access (unlimited messages catalog tier)"
)
SHELA001_DESCRIPTION = (
    "Shela offer — Premium features with 2000 message quota"
)
NOAM000_DESCRIPTION = (
    "Noam offer — lifetime Premium access (unlimited messages catalog tier)"
)


@dataclass(frozen=True)
class _CouponSpec:
    code: str
    description: str
    plan_granted: str = "premium"
    messages_limit: int | None = None  # None = follow plan tier cap
    max_uses: int | None = None  # None = unlimited redemptions globally


DEFAULT_COUPONS: tuple[_CouponSpec, ...] = (
    _CouponSpec("BSD100", BSD100_DESCRIPTION),
    _CouponSpec("SHELA000", SHELA000_DESCRIPTION, max_uses=1),
    _CouponSpec("SHELA001", SHELA001_DESCRIPTION, messages_limit=2000, max_uses=1),
    _CouponSpec("NOAM000", NOAM000_DESCRIPTION, max_uses=1),
)

# Backward-compatible alias for tests/scripts
DEFAULT_PREMIUM_COUPONS = DEFAULT_COUPONS


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


def _ensure_coupon(db: Session, spec: _CouponSpec) -> None:
    """Create or align one coupon row."""
    existing = db.query(Coupon).filter(Coupon.code == spec.code).first()
    if existing:
        changed = False
        if existing.plan_granted != spec.plan_granted:
            existing.plan_granted = spec.plan_granted
            changed = True
        if not existing.is_active:
            existing.is_active = True
            changed = True
        if (existing.description or "") != spec.description:
            existing.description = spec.description
            changed = True
        if existing.messages_limit != spec.messages_limit:
            existing.messages_limit = spec.messages_limit
            changed = True
        if existing.max_uses != spec.max_uses:
            existing.max_uses = spec.max_uses
            changed = True
        if changed:
            db.commit()
            logger.info("%s coupon aligned (plan/active/description/limit/max_uses)", spec.code)
        return

    db.add(
        Coupon(
            code=spec.code,
            plan_granted=spec.plan_granted,
            duration_days=None,
            max_uses=spec.max_uses,
            current_uses=0,
            is_active=True,
            expires_at=None,
            description=spec.description,
            messages_limit=spec.messages_limit,
        )
    )
    db.commit()
    logger.info("%s coupon created", spec.code)


def ensure_default_coupons(db: Session, *, _ddl_retry: bool = False) -> None:
    """
    Guarantee default coupons exist and are active.

    Safe under multi-worker Gunicorn: duplicate inserts raise IntegrityError → rollback.
    If `coupons` is missing, attempts SQLAlchemy DDL once then retries.
    """
    try:
        for spec in DEFAULT_COUPONS:
            _ensure_coupon(db, spec)
    except IntegrityError:
        db.rollback()
        logger.debug("Default coupon insert raced or duplicate; treating as ok")
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        if _ddl_retry:
            logger.warning("Default coupon bootstrap failed after DDL retry: %s", e)
            return
        logger.warning("Default coupon bootstrap DB error (will try DDL once): %s", e)
        if _maybe_create_coupon_tables():
            ensure_default_coupons(db, _ddl_retry=True)


def ensure_bsd100_coupon(db: Session, *, _ddl_retry: bool = False) -> None:
    """Backward-compatible alias — ensures all default coupons."""
    ensure_default_coupons(db, _ddl_retry=_ddl_retry)
