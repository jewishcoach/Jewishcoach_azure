"""
Billing and subscription management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
import os

from ..database import get_db
from ..models import User, Subscription, UsageRecord, Coupon, CouponRedemption
from ..dependencies import get_current_user
from ..schemas.billing import (
    CouponRedeemRequest,
    PlanInfo,
    SubscriptionResponse,
    UsageResponse,
    BillingOverviewResponse,
    PLAN_LIMITS,
    PlanType
)

router = APIRouter(prefix="/api/billing", tags=["billing"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_or_create_current_usage(db: Session, user: User) -> UsageRecord:
    """Get or create usage record for current billing period"""
    now = datetime.utcnow()
    
    # Find current period usage
    current_usage = db.query(UsageRecord).filter(
        UsageRecord.user_id == user.id,
        UsageRecord.period_start <= now,
        UsageRecord.period_end >= now
    ).first()
    
    if current_usage:
        return current_usage
    
    # Create new usage record for this month
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Next month
    if now.month == 12:
        period_end = period_start.replace(year=now.year + 1, month=1)
    else:
        period_end = period_start.replace(month=now.month + 1)
    
    new_usage = UsageRecord(
        user_id=user.id,
        period_start=period_start,
        period_end=period_end,
        messages_used=0,
        speech_minutes_used=0
    )
    db.add(new_usage)
    db.commit()
    db.refresh(new_usage)
    return new_usage


def check_usage_limit(db: Session, user: User, usage_type: str = "message") -> bool:
    """Check if user has quota available"""
    plan_limits = PLAN_LIMITS.get(user.current_plan, PLAN_LIMITS["basic"])
    usage = get_or_create_current_usage(db, user)
    
    if usage_type == "message":
        limit = plan_limits["messages_per_month"]
        if limit == -1:  # Unlimited
            return True
        return usage.messages_used < limit
    
    elif usage_type == "speech":
        limit = plan_limits["speech_minutes_per_month"]
        if limit == -1:  # Unlimited
            return True
        return usage.speech_minutes_used < limit
    
    return False


def increment_usage(db: Session, user: User, usage_type: str = "message", amount: int = 1):
    """Increment usage counter"""
    usage = get_or_create_current_usage(db, user)
    
    if usage_type == "message":
        usage.messages_used += amount
    elif usage_type == "speech":
        usage.speech_minutes_used += amount
    
    db.commit()


def get_active_coupon(db: Session, user: User) -> CouponRedemption | None:
    """Get user's active coupon redemption if exists"""
    now = datetime.utcnow()
    return db.query(CouponRedemption).filter(
        CouponRedemption.user_id == user.id,
        CouponRedemption.is_active == True,
        (CouponRedemption.expires_at.is_(None)) | (CouponRedemption.expires_at > now)
    ).first()


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/plans", response_model=List[PlanInfo])
def get_available_plans():
    """Get all available subscription plans"""
    plans = []
    for plan_id, plan_data in PLAN_LIMITS.items():
        plans.append(PlanInfo(
            id=plan_id,
            **plan_data
        ))
    return plans


@router.get("/overview", response_model=BillingOverviewResponse)
def get_billing_overview(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complete billing overview for current user"""
    
    # Get current subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.status == "active"
    ).first()
    
    # Get usage
    usage_record = get_or_create_current_usage(db, user)
    plan_limits = PLAN_LIMITS.get(user.current_plan, PLAN_LIMITS["basic"])
    
    usage = UsageResponse(
        period_start=usage_record.period_start,
        period_end=usage_record.period_end,
        messages_used=usage_record.messages_used,
        messages_limit=plan_limits["messages_per_month"],
        speech_minutes_used=usage_record.speech_minutes_used,
        speech_minutes_limit=plan_limits["speech_minutes_per_month"],
        plan=user.current_plan
    )
    
    # Get available plans
    available_plans = []
    for plan_id, plan_data in PLAN_LIMITS.items():
        available_plans.append(PlanInfo(id=plan_id, **plan_data))
    
    # Check for active coupon
    active_coupon = get_active_coupon(db, user)
    
    return BillingOverviewResponse(
        current_plan=user.current_plan,
        subscription=SubscriptionResponse.from_orm(subscription) if subscription else None,
        usage=usage,
        available_plans=available_plans,
        has_active_coupon=active_coupon is not None,
        coupon_code=active_coupon.coupon.code if active_coupon else None
    )


@router.post("/redeem-coupon")
def redeem_coupon(
    request: CouponRedeemRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Redeem a promotional coupon"""
    
    # Find coupon
    coupon = db.query(Coupon).filter(
        Coupon.code == request.code.upper(),
        Coupon.is_active == True
    ).first()
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found or inactive")
    
    # Check if coupon is expired
    if coupon.expires_at and coupon.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Coupon has expired")
    
    # Check if max uses reached
    if coupon.max_uses and coupon.current_uses >= coupon.max_uses:
        raise HTTPException(status_code=400, detail="Coupon usage limit reached")
    
    # Check if user already redeemed this coupon
    existing = db.query(CouponRedemption).filter(
        CouponRedemption.user_id == user.id,
        CouponRedemption.coupon_id == coupon.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You have already redeemed this coupon")
    
    # Calculate expiration
    expires_at = None
    if coupon.duration_days:
        expires_at = datetime.utcnow() + timedelta(days=coupon.duration_days)
    
    # Create redemption
    redemption = CouponRedemption(
        user_id=user.id,
        coupon_id=coupon.id,
        expires_at=expires_at,
        is_active=True
    )
    db.add(redemption)
    
    # Update coupon usage
    coupon.current_uses += 1
    
    # Update user plan
    user.current_plan = coupon.plan_granted
    
    # Create/update subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.status == "active"
    ).first()
    
    if subscription:
        subscription.plan = coupon.plan_granted
        subscription.coupon_code = coupon.code
        if expires_at:
            subscription.current_period_end = expires_at
    else:
        subscription = Subscription(
            user_id=user.id,
            plan=coupon.plan_granted,
            status="active",
            coupon_code=coupon.code,
            current_period_start=datetime.utcnow(),
            current_period_end=expires_at
        )
        db.add(subscription)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Coupon {coupon.code} redeemed successfully!",
        "plan_granted": coupon.plan_granted,
        "expires_at": expires_at
    }


@router.get("/usage", response_model=UsageResponse)
def get_current_usage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current billing period usage"""
    usage_record = get_or_create_current_usage(db, user)
    plan_limits = PLAN_LIMITS.get(user.current_plan, PLAN_LIMITS["basic"])
    
    return UsageResponse(
        period_start=usage_record.period_start,
        period_end=usage_record.period_end,
        messages_used=usage_record.messages_used,
        messages_limit=plan_limits["messages_per_month"],
        speech_minutes_used=usage_record.speech_minutes_used,
        speech_minutes_limit=plan_limits["speech_minutes_per_month"],
        plan=user.current_plan
    )


@router.post("/check-limit/{usage_type}")
def check_limit(
    usage_type: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has quota available for specific usage type"""
    has_quota = check_usage_limit(db, user, usage_type)
    
    if not has_quota:
        usage = get_or_create_current_usage(db, user)
        plan_limits = PLAN_LIMITS.get(user.current_plan, PLAN_LIMITS["basic"])
        
        return {
            "has_quota": False,
            "message": f"You have reached your {usage_type} limit for this billing period",
            "current_plan": user.current_plan,
            "upgrade_available": user.current_plan != "pro"
        }
    
    return {
        "has_quota": True
    }



