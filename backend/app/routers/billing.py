"""
Billing and subscription management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import List
import json
import secrets
import uuid

from ..database import get_db
from ..models import User, Subscription, UsageRecord, Coupon, CouponRedemption, Message, Conversation, PayMeCheckoutIntent
from ..dependencies import get_current_user
from ..schemas.billing import (
    CouponRedeemRequest,
    PlanInfo,
    SubscriptionResponse,
    UsageResponse,
    BillingOverviewResponse,
    PayMeCheckoutClientConfig,
    PLAN_LIMITS,
    BILLING_PLANS_IN_CATALOG,
    PayMeSubscribeRequest,
    effective_messages_per_month,
)
from ..services.payme_settings import (
    payme_api_base_url,
    payme_api_key,
    payme_webhook_secret,
    payme_is_ready_for_requests,
)
from ..services.payme_api import (
    payme_generate_sale,
    payme_response_failed,
    payme_sale_reference,
    PayMeAPIError,
    deep_find_transaction_id,
    webhook_payload_suggests_success,
)

router = APIRouter(prefix="/api/billing", tags=["billing"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def count_user_messages_quota_usage(db: Session, user_id: int) -> int:
    """All-time count of user (quota) messages — used for plan limits (one-time / lifetime quota model)."""
    n = (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user_id, Message.role == "user")
        .scalar()
    )
    return int(n or 0)


def sync_usage_messages_used(db: Session, usage: UsageRecord) -> int:
    """Mirror lifetime user message count onto the active Usage row (speech still uses monthly periods)."""
    n = count_user_messages_quota_usage(db, usage.user_id)
    if usage.messages_used != n:
        usage.messages_used = n
        db.commit()
        db.refresh(usage)
    return n


def get_or_create_current_usage(db: Session, user: User) -> UsageRecord:
    """Get or create usage record for current billing period"""
    now = datetime.now(timezone.utc)
    
    # Find current period usage
    current_usage = db.query(UsageRecord).filter(
        UsageRecord.user_id == user.id,
        UsageRecord.period_start <= now,
        UsageRecord.period_end > now,
    ).first()
    
    if current_usage:
        sync_usage_messages_used(db, current_usage)
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
    sync_usage_messages_used(db, new_usage)
    return new_usage


def check_usage_limit(db: Session, user: User, usage_type: str = "message") -> bool:
    """Check if user has quota available"""
    plan_limits = PLAN_LIMITS.get(user.current_plan, PLAN_LIMITS["basic"])

    if usage_type == "message":
        limit = effective_messages_per_month(
            email=user.email, plan_key=user.current_plan, clerk_id=user.clerk_id
        )
        if limit == -1:  # Unlimited
            return True
        used = count_user_messages_quota_usage(db, user.id)
        return used < limit

    elif usage_type == "speech":
        usage = get_or_create_current_usage(db, user)
        limit = plan_limits["speech_minutes_per_month"]
        if limit == -1:  # Unlimited
            return True
        return usage.speech_minutes_used < limit

    return False


def increment_usage(db: Session, user: User, usage_type: str = "message", amount: int = 1):
    """Increment usage counter (speech only; message counts come from the Message table)."""
    if usage_type == "message":
        return
    usage = get_or_create_current_usage(db, user)
    if usage_type == "speech":
        usage.speech_minutes_used += amount
    
    db.commit()


def get_active_coupon(db: Session, user: User) -> CouponRedemption | None:
    """Get user's active coupon redemption if exists"""
    now = datetime.now(timezone.utc)
    return db.query(CouponRedemption).filter(
        CouponRedemption.user_id == user.id,
        CouponRedemption.is_active == True,
        (CouponRedemption.expires_at.is_(None)) | (CouponRedemption.expires_at > now)
    ).first()


def _payme_plan_rank(plan_key: str) -> int:
    """Higher = better tier (used to block downgrades via checkout)."""
    return {"basic": 0, "premium": 1, "pro": 2}.get(plan_key, 0)


def _apply_payme_paid_plan(
    db: Session,
    user: User,
    plan: str,
    transaction_id: str,
    payme_resp: dict | None,
) -> None:
    """Grant paid plan after successful PayMe payment (one-time unlock)."""
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=31)
    user.current_plan = plan
    sale_ref = payme_sale_reference(payme_resp or {})
    ext_id = f"payme:{sale_ref}" if sale_ref else f"payme_tx:{transaction_id}"
    sub = db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.status == "active",
    ).first()
    if sub:
        sub.plan = plan
        sub.status = "active"
        sub.stripe_subscription_id = ext_id
        sub.coupon_code = None
        sub.current_period_start = now
        sub.current_period_end = period_end
    else:
        db.add(
            Subscription(
                user_id=user.id,
                plan=plan,
                status="active",
                stripe_subscription_id=ext_id,
                current_period_start=now,
                current_period_end=period_end,
            )
        )


def _public_payme_snapshot(d: dict) -> dict:
    keys = ("status_code", "session", "pay_me_sale_id", "sale_pay_me_id", "sale_id")
    return {k: d[k] for k in keys if k in d}


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/payme/status")
def payme_integration_status(_user: User = Depends(get_current_user)):
    """
    Whether PayMe env is configured on the server (no secrets returned).
    Full checkout/webhook flow still requires implementation against PayMe API docs.
    """
    return {
        "payme_api_key_configured": bool(payme_api_key()),
        "payme_api_base_configured": bool(payme_api_base_url()),
        "payme_webhook_secret_configured": bool(payme_webhook_secret()),
        "payme_ready_for_http": payme_is_ready_for_requests(),
    }


@router.get("/payme/checkout-config")
def payme_checkout_client_config(_user: User = Depends(get_current_user)):
    """Merchant key + mode for PayMe Hosted Fields (browser). Same pattern as PayMe JS examples."""
    if not payme_is_ready_for_requests():
        raise HTTPException(status_code=503, detail="PayMe is not configured on the server")
    base = payme_api_base_url()
    test_mode = "sandbox" in base.lower()
    return {
        "merchant_public_key": payme_api_key(),
        "test_mode": test_mode,
        "checkout_js_url": "https://cdn.payme.io/hf/v1/hostedfields.js",
    }


@router.post("/payme/subscribe")
def payme_subscribe_with_token(
    body: PayMeSubscribeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Charge saved-card token from PayMe Hosted Fields and upgrade the user's plan.
    """
    if not payme_is_ready_for_requests():
        raise HTTPException(status_code=503, detail="PayMe is not configured")

    plan = body.plan
    if plan != "premium":
        raise HTTPException(status_code=400, detail="Invalid plan")

    if user.current_plan == plan:
        raise HTTPException(status_code=400, detail="Already subscribed to this plan")

    if _payme_plan_rank(plan) < _payme_plan_rank(user.current_plan):
        raise HTTPException(status_code=400, detail="Downgrades are not handled via PayMe checkout")

    price = int(PLAN_LIMITS[plan]["price"])
    if price <= 0:
        raise HTTPException(status_code=400, detail="Plan has no price")

    tid = f"jc-{user.id}-{uuid.uuid4().hex}"

    intent = PayMeCheckoutIntent(
        user_id=user.id,
        plan=plan,
        transaction_id=tid,
    )
    db.add(intent)
    db.commit()

    payer_email = (body.payer_email or user.email or "").strip()

    try:
        resp = payme_generate_sale(
            buyer_token=body.buyer_token,
            sale_price=price,
            transaction_id=tid,
            buyer_email=payer_email or None,
        )
    except PayMeAPIError as e:
        intent.last_payme_json = json.dumps(e.body if isinstance(e.body, dict) else {"error": str(e.body)})[:8000]
        db.commit()
        raise HTTPException(status_code=502, detail=f"PayMe request failed: {e}") from e

    intent.last_payme_json = json.dumps(resp)[:8000]
    db.commit()

    if payme_response_failed(resp):
        detail = resp.get("status_error_details") or "Payment declined"
        raise HTTPException(status_code=402, detail=str(detail))

    intent.fulfilled_at = datetime.now(timezone.utc)
    _apply_payme_paid_plan(db, user, plan, tid, resp)
    db.commit()

    return {
        "success": True,
        "plan": plan,
        "transaction_id": tid,
        "payme": _public_payme_snapshot(resp),
    }


@router.post("/payme/webhook")
async def payme_webhook_handler(request: Request, db: Session = Depends(get_db)):
    """
    PayMe server callbacks — configure URL in PayMe dashboard.
    Optional shared secret: set PAYME_WEBHOOK_SECRET and send the same value in header X-PayMe-Webhook-Token.
    """
    raw = await request.body()
    secret = payme_webhook_secret()
    if secret:
        tok = (
            request.headers.get("X-PayMe-Webhook-Token")
            or request.headers.get("X-Payme-Webhook-Token")
            or ""
        ).strip()
        ok_match = False
        try:
            ok_match = bool(tok and secrets.compare_digest(tok, secret))
        except ValueError:
            ok_match = False
        if not ok_match:
            raise HTTPException(status_code=401, detail="Invalid webhook token")

    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    tid = deep_find_transaction_id(payload)
    if not tid:
        return {"received": True, "matched": False}

    intent = (
        db.query(PayMeCheckoutIntent)
        .filter(
            PayMeCheckoutIntent.transaction_id == tid,
            PayMeCheckoutIntent.fulfilled_at.is_(None),
        )
        .first()
    )
    if not intent:
        return {"received": True, "matched": False}

    if not webhook_payload_suggests_success(payload):
        return {"received": True, "matched": True, "fulfilled": False}

    user = db.query(User).filter(User.id == intent.user_id).first()
    if not user:
        return {"received": True, "matched": False}

    intent.fulfilled_at = datetime.now(timezone.utc)
    intent.last_payme_json = json.dumps(payload)[:8000]
    _apply_payme_paid_plan(db, user, intent.plan, tid, payload if isinstance(payload, dict) else None)
    db.commit()
    return {"received": True, "matched": True, "fulfilled": True}


@router.get("/plans", response_model=List[PlanInfo])
def get_available_plans():
    """Get subscription plans offered in the product catalog (Basic + Premium)."""
    return [
        PlanInfo(id=plan_id, **PLAN_LIMITS[plan_id])
        for plan_id in BILLING_PLANS_IN_CATALOG
    ]


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
        messages_used=count_user_messages_quota_usage(db, user.id),
        messages_limit=effective_messages_per_month(
            email=user.email, plan_key=user.current_plan, clerk_id=user.clerk_id
        ),
        speech_minutes_used=usage_record.speech_minutes_used,
        speech_minutes_limit=plan_limits["speech_minutes_per_month"],
        plan=user.current_plan
    )
    
    available_plans = [
        PlanInfo(id=plan_id, **PLAN_LIMITS[plan_id])
        for plan_id in BILLING_PLANS_IN_CATALOG
    ]
    
    # Check for active coupon
    active_coupon = get_active_coupon(db, user)

    payme_checkout: PayMeCheckoutClientConfig | None = None
    if payme_is_ready_for_requests():
        base = payme_api_base_url()
        payme_checkout = PayMeCheckoutClientConfig(
            merchant_public_key=payme_api_key(),
            test_mode="sandbox" in base.lower(),
            checkout_js_url="https://cdn.payme.io/hf/v1/hostedfields.js",
        )

    return BillingOverviewResponse(
        current_plan=user.current_plan,
        subscription=SubscriptionResponse.from_orm(subscription) if subscription else None,
        usage=usage,
        available_plans=available_plans,
        has_active_coupon=active_coupon is not None,
        coupon_code=active_coupon.coupon.code if active_coupon else None,
        payme_checkout=payme_checkout,
    )


@router.post("/redeem-coupon")
def redeem_coupon(
    request: CouponRedeemRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Redeem a promotional coupon"""
    from ..services.coupon_bootstrap import ensure_bsd100_coupon

    # Lazily ensure default coupons exist even if worker lifespan missed or table was created late.
    ensure_bsd100_coupon(db)

    code_norm = (request.code or "").strip().upper()
    if not code_norm:
        raise HTTPException(status_code=400, detail={"error": "coupon_empty"})

    row = db.query(Coupon).filter(Coupon.code == code_norm).first()
    if not row or not row.is_active:
        raise HTTPException(status_code=400, detail={"error": "coupon_invalid"})

    coupon = row
    
    # Check if coupon is expired
    if coupon.expires_at and coupon.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail={"error": "coupon_invalid"})
    
    # Check if max uses reached
    if coupon.max_uses and coupon.current_uses >= coupon.max_uses:
        raise HTTPException(status_code=400, detail={"error": "coupon_invalid"})
    
    # Check if user already redeemed this coupon
    existing = db.query(CouponRedemption).filter(
        CouponRedemption.user_id == user.id,
        CouponRedemption.coupon_id == coupon.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail={"error": "coupon_already_redeemed"})
    
    # Calculate expiration
    expires_at = None
    if coupon.duration_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=coupon.duration_days)
    
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
            current_period_start=datetime.now(timezone.utc),
            current_period_end=expires_at
        )
        db.add(subscription)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Coupon redeemed successfully.",
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
        messages_used=count_user_messages_quota_usage(db, user.id),
        messages_limit=effective_messages_per_month(
            email=user.email, plan_key=user.current_plan, clerk_id=user.clerk_id
        ),
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
            "message": (
                f"You have reached your {usage_type} limit for your plan"
                if usage_type == "message"
                else f"You have reached your {usage_type} limit for this billing period"
            ),
            "current_plan": user.current_plan,
            "upgrade_available": user.current_plan == "basic"
        }
    
    return {
        "has_quota": True
    }



