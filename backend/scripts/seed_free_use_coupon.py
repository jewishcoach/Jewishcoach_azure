"""
Ensure a coupon exists that grants unlimited messaging (Premium or PRO tier).

Premium matches the public catalog (unlimited messages). Use PRO for the legacy
full-feature tier (same message cap + extra flags in PLAN_LIMITS).

Configure via env:
  FREE_USE_COUPON_CODE   — required meaningful secret in production (default JC_FREE_ACCESS for dev only)
  FREE_USE_PLAN_GRANTED  — premium | pro (default premium)

Run from backend dir:
  cd backend && FREE_USE_COUPON_CODE=MYSECRET python -m scripts.seed_free_use_coupon

Azure App Service example:
  FREE_USE_COUPON_CODE=<paste-strong-secret>
  FREE_USE_PLAN_GRANTED=premium
"""
from __future__ import annotations

import os
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Coupon
from app.schemas.billing import PLAN_LIMITS


DEFAULT_CODE = "JC_FREE_ACCESS"
DEFAULT_PLAN = "premium"


def _normalize_plan(raw: str) -> str:
    p = raw.strip().lower()
    if p not in PLAN_LIMITS:
        raise SystemExit(f"FREE_USE_PLAN_GRANTED must be one of {list(PLAN_LIMITS.keys())}, got {raw!r}")
    cap = PLAN_LIMITS[p]["messages_per_month"]
    if cap != -1:
        raise SystemExit(
            f"Plan {p!r} does not include unlimited messages (messages_per_month={cap}). "
            "Use premium or pro."
        )
    return p


def seed_free_use_coupon() -> None:
    if os.environ.get("FREE_USE_COUPON_CODE") is None:
        print(
            "WARNING: FREE_USE_COUPON_CODE is not set — using default "
            f"{DEFAULT_CODE!r}. Set a secret code in production.\n"
        )

    code = (os.environ.get("FREE_USE_COUPON_CODE") or DEFAULT_CODE).strip().upper()
    if len(code) < 4:
        raise SystemExit("Coupon code must be at least 4 characters.")

    plan = _normalize_plan(os.environ.get("FREE_USE_PLAN_GRANTED") or DEFAULT_PLAN)

    db: Session = SessionLocal()
    try:
        existing = db.query(Coupon).filter(Coupon.code == code).first()
        if existing:
            changed = False
            if existing.plan_granted != plan:
                print(f"Updating plan_granted: {existing.plan_granted!r} -> {plan!r}")
                existing.plan_granted = plan
                changed = True
            if not existing.is_active:
                print("Re-activating coupon.")
                existing.is_active = True
                changed = True
            if changed:
                db.commit()
            print(f"OK — coupon {code!r} exists (plan={existing.plan_granted}, active={existing.is_active}).")
            return

        coupon = Coupon(
            code=code,
            plan_granted=plan,
            duration_days=None,
            max_uses=None,
            current_uses=0,
            is_active=True,
            expires_at=None,
            description="Free-use coupon — unlimited messages tier (seeded via scripts.seed_free_use_coupon)",
        )
        db.add(coupon)
        db.commit()
        db.refresh(coupon)
        print(f"Created coupon {code!r} -> plan={plan} (lifetime, unlimited redemptions).")
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding free-use coupon…\n")
    seed_free_use_coupon()
