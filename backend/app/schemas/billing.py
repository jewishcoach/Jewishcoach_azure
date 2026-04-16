"""
Pydantic schemas for billing and subscription management
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class PlanType(str, Enum):
    """Subscription plan types"""
    BASIC = "basic"
    PREMIUM = "premium"
    PRO = "pro"


class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"
    TRIAL = "trial"


# Plan Definitions
PLAN_LIMITS = {
    "basic": {
        "name_he": "בסיסי",
        "name_en": "Basic",
        "price": 0,
        "currency": "ILS",
        "messages_per_month": 1000,
        # תמלול קולי: ללא הגבלה זמנית לכל התוכניות (עד להודעה חדשה)
        "speech_minutes_per_month": -1,
        "features": {
            "coaching_phases": ["Situation", "Gap"],
            "journal_access": True,
            "advanced_tools": False,
            "priority_support": False
        }
    },
    "premium": {
        "name_he": "פרמיום",
        "name_en": "Premium",
        "price": 89,
        "currency": "ILS",
        "messages_per_month": 100,
        "speech_minutes_per_month": -1,
        "features": {
            "coaching_phases": "all",  # All 9 phases
            "journal_access": True,
            "advanced_tools": True,
            "priority_support": False
        }
    },
    "pro": {
        "name_he": "מקצועי",
        "name_en": "Pro",
        "price": 249,
        "currency": "ILS",
        "messages_per_month": -1,  # Unlimited
        "speech_minutes_per_month": -1,  # Unlimited
        "features": {
            "coaching_phases": "all",
            "journal_access": True,
            "advanced_tools": True,
            "priority_support": True,
            "advanced_reports": True,
            "api_access": True
        }
    }
}


# Per-account monthly message caps. Keys use quota_email_key() so Gmail variants match.
MESSAGE_LIMIT_OVERRIDES_BY_EMAIL: dict[str, int] = {
    "mormay11@gmail.com": 10_000,  # mor.may11@gmail.com — Gmail ignores dots in local part
}

# When Clerk has not synced a real email yet, user.email may be "{clerk_id}@clerk.temp" — overrides by clerk_id still apply.
MESSAGE_LIMIT_OVERRIDES_BY_CLERK_ID: dict[str, int] = {
    "user_3BeVDVjqPMZCyHr3H4dWPyiileW": 10_000,
}


def quota_email_key(email: Optional[str]) -> str:
    """
    Stable key for quota overrides: lowercase, strip; Gmail/Googlemail: dots removed from local part.
    """
    raw = (email or "").strip().lower()
    if "@" not in raw:
        return raw
    local, _, domain = raw.partition("@")
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
    return f"{local}@{domain}"


def effective_messages_per_month(
    *, email: Optional[str], plan_key: str, clerk_id: Optional[str] = None
) -> int:
    """Resolved message cap for the billing period (plan unlimited wins, then clerk_id, then email override)."""
    plan_limits = PLAN_LIMITS.get(plan_key, PLAN_LIMITS["basic"])
    plan_cap = plan_limits["messages_per_month"]
    if plan_cap == -1:
        return -1
    cid = (clerk_id or "").strip()
    if cid in MESSAGE_LIMIT_OVERRIDES_BY_CLERK_ID:
        return MESSAGE_LIMIT_OVERRIDES_BY_CLERK_ID[cid]
    key = quota_email_key(email)
    if key in MESSAGE_LIMIT_OVERRIDES_BY_EMAIL:
        return MESSAGE_LIMIT_OVERRIDES_BY_EMAIL[key]
    return plan_cap


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class CouponRedeemRequest(BaseModel):
    """Request to redeem a coupon"""
    code: str = Field(..., description="Coupon code (e.g., BSD100)")


class CreateCheckoutSessionRequest(BaseModel):
    """Request to create Stripe checkout session"""
    plan: PlanType
    success_url: str
    cancel_url: str


class CancelSubscriptionRequest(BaseModel):
    """Request to cancel subscription"""
    cancel_at_period_end: bool = True  # If False, cancel immediately


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class PlanInfo(BaseModel):
    """Plan information"""
    id: str
    name_he: str
    name_en: str
    price: int
    currency: str
    messages_per_month: int
    speech_minutes_per_month: int
    features: dict

    model_config = ConfigDict(from_attributes=True)


class SubscriptionResponse(BaseModel):
    """Subscription details"""
    id: int
    user_id: int
    plan: str
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    coupon_code: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UsageResponse(BaseModel):
    """Current usage statistics"""
    period_start: datetime
    period_end: datetime
    messages_used: int
    messages_limit: int
    speech_minutes_used: int
    speech_minutes_limit: int
    plan: str

    model_config = ConfigDict(from_attributes=True)


class CouponResponse(BaseModel):
    """Coupon information"""
    code: str
    plan_granted: str
    duration_days: Optional[int]
    description: Optional[str]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class BillingOverviewResponse(BaseModel):
    """Complete billing overview"""
    current_plan: str
    subscription: Optional[SubscriptionResponse]
    usage: UsageResponse
    available_plans: list[PlanInfo]
    has_active_coupon: bool
    coupon_code: Optional[str]

    model_config = ConfigDict(from_attributes=True)



