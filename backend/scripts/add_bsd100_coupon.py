"""
Script to add or verify BSD100 coupon
Run with: python -m scripts.add_bsd100_coupon
"""
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Coupon


BSD100_DESCRIPTION = (
    "BSD Special Launch Offer — lifetime Premium access (unlimited messages catalog tier)"
)


def add_bsd100_coupon():
    """Add or align BSD100 coupon (grants Premium)."""
    db: Session = SessionLocal()
    
    try:
        existing = db.query(Coupon).filter(Coupon.code == "BSD100").first()
        
        if existing:
            changed = False
            if existing.plan_granted != "premium":
                print(f"↻ Updating BSD100 plan_granted: {existing.plan_granted!r} → 'premium'")
                existing.plan_granted = "premium"
                changed = True
            if (existing.description or "") != BSD100_DESCRIPTION:
                existing.description = BSD100_DESCRIPTION
                changed = True
            if changed:
                db.commit()
                db.refresh(existing)
            print("✅ BSD100 coupon already exists!")
            print(f"   Plan: {existing.plan_granted}")
            print(f"   Active: {existing.is_active}")
            print(f"   Uses: {existing.current_uses}/{existing.max_uses or 'unlimited'}")
            print(f"   Duration: {'Lifetime' if not existing.duration_days else f'{existing.duration_days} days'}")
            print("\n🎉 Redeeming BSD100 grants lifetime Premium.")
            return
        
        coupon = Coupon(
            code="BSD100",
            plan_granted="premium",
            duration_days=None,  # Lifetime
            max_uses=None,  # Unlimited uses
            current_uses=0,
            is_active=True,
            expires_at=None,  # Never expires
            description=BSD100_DESCRIPTION,
        )
        
        db.add(coupon)
        db.commit()
        db.refresh(coupon)
        
        print("✅ BSD100 coupon created successfully!")
        print(f"   ID: {coupon.id}")
        print(f"   Code: {coupon.code}")
        print(f"   Plan: {coupon.plan_granted}")
        print(f"   Duration: Lifetime")
        print(f"   Max Uses: Unlimited")
        print("\n🎉 Users can now redeem BSD100 for lifetime Premium access!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🎫 Adding BSD100 coupon...\n")
    add_bsd100_coupon()



