"""
Script to add or verify BSD100 coupon
Run with: python -m scripts.add_bsd100_coupon
"""
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Coupon
from datetime import datetime


def add_bsd100_coupon():
    """Add BSD100 coupon to database"""
    db: Session = SessionLocal()
    
    try:
        # Check if coupon already exists
        existing = db.query(Coupon).filter(Coupon.code == "BSD100").first()
        
        if existing:
            print(f"✅ BSD100 coupon already exists!")
            print(f"   Plan: {existing.plan_granted}")
            print(f"   Active: {existing.is_active}")
            print(f"   Uses: {existing.current_uses}/{existing.max_uses or 'unlimited'}")
            print(f"   Duration: {'Lifetime' if not existing.duration_days else f'{existing.duration_days} days'}")
            return
        
        # Create new coupon
        coupon = Coupon(
            code="BSD100",
            plan_granted="pro",
            duration_days=None,  # Lifetime
            max_uses=None,  # Unlimited uses
            current_uses=0,
            is_active=True,
            expires_at=None,  # Never expires
            description="BSD Special Launch Offer - Lifetime PRO access for early adopters"
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
        print("\n🎉 Users can now redeem BSD100 for lifetime PRO access!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🎫 Adding BSD100 coupon...\n")
    add_bsd100_coupon()



