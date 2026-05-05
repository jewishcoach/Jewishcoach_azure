"""
Script to add or verify BSD100 coupon
Run with: python -m scripts.add_bsd100_coupon
"""
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Coupon
from app.services.coupon_bootstrap import ensure_bsd100_coupon


def add_bsd100_coupon():
    """Add or align BSD100 coupon (grants Premium)."""
    db: Session = SessionLocal()

    try:
        ensure_bsd100_coupon(db)
        existing = db.query(Coupon).filter(Coupon.code == "BSD100").first()
        if not existing:
            print("❌ BSD100 coupon is still missing (coupons table or DB connectivity)")
            return

        print("✅ BSD100 coupon OK")
        print(f"   ID: {existing.id}")
        print(f"   Code: {existing.code}")
        print(f"   Plan: {existing.plan_granted}")
        print(f"   Active: {existing.is_active}")
        print(f"   Uses: {existing.current_uses}/{existing.max_uses or 'unlimited'}")
        print(f"   Duration: {'Lifetime' if not existing.duration_days else f'{existing.duration_days} days'}")
        print("\n🎉 Redeeming BSD100 grants lifetime Premium.")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🎫 Adding BSD100 coupon...\n")
    add_bsd100_coupon()
