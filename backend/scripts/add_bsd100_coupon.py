"""
Script to add or verify default Premium coupons (BSD100, SHELA000, …).
Run with: python -m scripts.add_bsd100_coupon
"""
from app.database import SessionLocal
from app.models import Coupon
from app.services.coupon_bootstrap import DEFAULT_PREMIUM_COUPONS, ensure_default_coupons


def verify_default_coupons() -> None:
    """Add or align all default lifetime Premium coupons."""
    db = SessionLocal()
    try:
        ensure_default_coupons(db)
        ok = True
        for spec in DEFAULT_PREMIUM_COUPONS:
            existing = db.query(Coupon).filter(Coupon.code == spec.code).first()
            if not existing:
                print(f"❌ {spec.code} coupon is still missing (coupons table or DB connectivity)")
                ok = False
                continue
            print(f"✅ {existing.code} coupon OK")
            print(f"   ID: {existing.id}")
            print(f"   Plan: {existing.plan_granted}")
            print(f"   Active: {existing.is_active}")
            print(f"   Message limit: {existing.messages_limit if existing.messages_limit is not None else 'plan default'}")
            print(f"   Max redemptions: {existing.max_uses if existing.max_uses is not None else 'unlimited'}")
            print(f"   Uses: {existing.current_uses}/{existing.max_uses or 'unlimited'}")
            print(
                f"   Duration: {'Lifetime' if not existing.duration_days else f'{existing.duration_days} days'}"
            )
            print()
        if ok:
            print("🎉 Redeeming any of the above grants lifetime Premium.")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🎫 Ensuring default Premium coupons...\n")
    verify_default_coupons()
