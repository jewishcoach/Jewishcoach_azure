"""
Admin API Endpoints

Protected endpoints for admin users to view quality flags,
system stats, user directory / usage summaries, and manage the LLM-as-a-Judge audit results.
"""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..dependencies import get_current_admin_user
from ..database import get_db
from ..models import ConversationFlag, User, Conversation, Message, UsageRecord, CouponRedemption
from ..schemas.billing import PLAN_LIMITS
from typing import Optional

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)]  # ALL routes require admin
)

@router.get("/flags")
async def get_all_flags(
    db: Session = Depends(get_db),
    resolved: Optional[bool] = None,
    severity: Optional[str] = None,
    issue_type: Optional[str] = None
):
    """
    List all quality flags with filters.
    
    Query params:
    - resolved: Filter by resolution status (true/false)
    - severity: Filter by severity ("High", "Medium", "Low")
    - issue_type: Filter by issue type ("Hallucination", "Advice", "Logic Error", "Methodology")
    """
    query = db.query(ConversationFlag)
    
    if resolved is not None:
        query = query.filter(ConversationFlag.is_resolved == resolved)
    if severity:
        query = query.filter(ConversationFlag.severity == severity)
    if issue_type:
        query = query.filter(ConversationFlag.issue_type == issue_type)
    
    flags = query.order_by(ConversationFlag.created_at.desc()).all()
    
    # Enrich flags with conversation and message details
    enriched_flags = []
    for flag in flags:
        conversation = db.query(Conversation).filter(Conversation.id == flag.conversation_id).first()
        message = db.query(Message).filter(Message.id == flag.message_id).first()
        
        enriched_flags.append({
            "id": flag.id,
            "conversation_id": flag.conversation_id,
            "conversation_title": conversation.title if conversation else "Unknown",
            "message_id": flag.message_id,
            "message_content": message.content[:100] + "..." if message and len(message.content) > 100 else message.content if message else "",
            "stage": flag.stage,
            "issue_type": flag.issue_type,
            "reasoning": flag.reasoning,
            "severity": flag.severity,
            "is_resolved": flag.is_resolved,
            "created_at": flag.created_at.isoformat()
        })
    
    return {"flags": enriched_flags, "total": len(enriched_flags)}

@router.get("/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """
    Get system-wide quality metrics.
    
    Returns:
    - Total flags count
    - Unresolved flags count
    - Breakdown by severity
    - Breakdown by issue type
    - Breakdown by stage
    """
    total_flags = db.query(ConversationFlag).count()
    unresolved = db.query(ConversationFlag).filter(ConversationFlag.is_resolved == False).count()
    
    by_severity = {
        "High": db.query(ConversationFlag).filter(ConversationFlag.severity == "High").count(),
        "Medium": db.query(ConversationFlag).filter(ConversationFlag.severity == "Medium").count(),
        "Low": db.query(ConversationFlag).filter(ConversationFlag.severity == "Low").count()
    }
    
    by_issue_type = {
        "Hallucination": db.query(ConversationFlag).filter(ConversationFlag.issue_type == "Hallucination").count(),
        "Advice": db.query(ConversationFlag).filter(ConversationFlag.issue_type == "Advice").count(),
        "Logic Error": db.query(ConversationFlag).filter(ConversationFlag.issue_type == "Logic Error").count(),
        "Methodology": db.query(ConversationFlag).filter(ConversationFlag.issue_type == "Methodology").count()
    }
    
    # Get stage breakdown
    stage_counts = {}
    all_flags = db.query(ConversationFlag).all()
    for flag in all_flags:
        stage_counts[flag.stage] = stage_counts.get(flag.stage, 0) + 1
    
    return {
        "total_flags": total_flags,
        "unresolved_flags": unresolved,
        "by_severity": by_severity,
        "by_issue_type": by_issue_type,
        "by_stage": stage_counts,
        "resolution_rate": round((total_flags - unresolved) / total_flags * 100, 1) if total_flags > 0 else 0
    }

@router.patch("/flags/{flag_id}/resolve")
async def resolve_flag(
    flag_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark a flag as resolved.
    
    This indicates the admin has reviewed the issue and taken action
    (e.g., improved prompts, updated methodology documentation).
    """
    flag = db.query(ConversationFlag).filter(ConversationFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    
    flag.is_resolved = True
    db.commit()
    return {"message": "Flag resolved", "flag_id": flag_id}

@router.get("/flags/{flag_id}")
async def get_flag_details(
    flag_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific flag,
    including the full conversation context.
    """
    flag = db.query(ConversationFlag).filter(ConversationFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    
    conversation = db.query(Conversation).filter(Conversation.id == flag.conversation_id).first()
    message = db.query(Message).filter(Message.id == flag.message_id).first()
    
    # Get surrounding messages for context (2 before, 2 after)
    all_messages = db.query(Message).filter(
        Message.conversation_id == flag.conversation_id
    ).order_by(Message.timestamp).all()
    
    # Find index of flagged message
    flagged_index = next((i for i, m in enumerate(all_messages) if m.id == flag.message_id), None)
    
    context_messages = []
    if flagged_index is not None:
        start = max(0, flagged_index - 2)
        end = min(len(all_messages), flagged_index + 3)
        context_messages = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "is_flagged": m.id == flag.message_id
            }
            for m in all_messages[start:end]
        ]
    
    return {
        "id": flag.id,
        "conversation_id": flag.conversation_id,
        "conversation_title": conversation.title if conversation else "Unknown",
        "message_id": flag.message_id,
        "stage": flag.stage,
        "issue_type": flag.issue_type,
        "reasoning": flag.reasoning,
        "severity": flag.severity,
        "is_resolved": flag.is_resolved,
        "created_at": flag.created_at.isoformat(),
        "context_messages": context_messages
    }


def _empty_user_agg() -> dict:
    return {
        "conversation_count": 0,
        "message_count": 0,
        "user_message_count": 0,
        "assistant_message_count": 0,
        "estimated_llm_tokens_approx": 0,
        "last_activity_at": None,
    }


def _parse_optional_float(env_key: str) -> Optional[float]:
    raw = os.getenv(env_key)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def economics_assumptions() -> dict:
    """
    Admin economics helpers (optional env):

    - ADMIN_LLM_USD_PER_MILLION_TOKENS — blended $ / 1M tokens for rough LLM COGS
      (multiply by estimated_llm_tokens_approx ≈ sum(chars)/4 over persisted messages).
    - ADMIN_ILS_PER_USD — FX to show estimated LLM cost and margin in ₪.

    Revenue shown is catalog list price from PLAN_LIMITS (ILS/month), not Stripe charges.
    """
    return {
        "llm_usd_per_million_tokens": _parse_optional_float("ADMIN_LLM_USD_PER_MILLION_TOKENS"),
        "ils_per_usd": _parse_optional_float("ADMIN_ILS_PER_USD"),
        "revenue_note": "catalog_list_price_ils_not_stripe_actuals",
        "cost_note": "llm_only_chars_over_4_proxy_not_azure_invoice",
    }


def _plan_catalog_price_ils(plan_key: Optional[str]) -> int:
    p = (plan_key or "basic").strip() or "basic"
    row = PLAN_LIMITS.get(p, PLAN_LIMITS["basic"])
    return int(row.get("price") or 0)


def _estimated_llm_cost_usd(tokens_approx: int, usd_per_million: Optional[float]) -> Optional[float]:
    if usd_per_million is None:
        return None
    if tokens_approx <= 0:
        return 0.0
    return round((tokens_approx / 1_000_000.0) * usd_per_million, 6)


def _users_with_active_coupon(db: Session, user_ids: list[int]) -> set[int]:
    if not user_ids:
        return set()
    now = datetime.now(timezone.utc)
    rows = (
        db.query(CouponRedemption.user_id)
        .filter(
            CouponRedemption.user_id.in_(user_ids),
            CouponRedemption.is_active.is_(True),
            or_(CouponRedemption.expires_at.is_(None), CouponRedemption.expires_at > now),
        )
        .distinct()
        .all()
    )
    return {int(r[0]) for r in rows}


def _economics_row(
    *,
    tokens_approx: int,
    plan_key: Optional[str],
    has_active_coupon: bool,
    assumptions: dict,
) -> dict:
    usd_rate = assumptions.get("llm_usd_per_million_tokens")
    fx = assumptions.get("ils_per_usd")
    cost_usd = _estimated_llm_cost_usd(tokens_approx, usd_rate)
    cost_ils = None
    if cost_usd is not None and fx is not None:
        cost_ils = round(cost_usd * fx, 2)
    catalog_ils = _plan_catalog_price_ils(plan_key)
    margin_ils = None
    if cost_ils is not None:
        margin_ils = round(catalog_ils - cost_ils, 2)
    return {
        "plan_list_price_ils_month": catalog_ils,
        "has_active_coupon": has_active_coupon,
        "estimated_llm_cost_usd": cost_usd,
        "estimated_llm_cost_ils": cost_ils,
        "estimated_margin_catalog_minus_llm_ils": margin_ils,
    }


def _aggregate_directory_totals(
    db: Session,
    matching_user_ids_subq,
    *,
    user_count: int,
    assumptions: dict,
) -> dict:
    """
    Rollups over every user matching the directory filter (not just the current page).
    Token methodology matches _aggregate_user_stats (sum over roles of floor(chars/4)).
    """
    if user_count <= 0:
        tokens = 0
        msgs = 0
    else:
        role_rows = (
            db.query(
                Conversation.user_id,
                Message.role,
                func.coalesce(func.sum(func.length(Message.content)), 0),
            )
            .join(Message, Message.conversation_id == Conversation.id)
            .filter(Conversation.user_id.in_(matching_user_ids_subq))
            .group_by(Conversation.user_id, Message.role)
            .all()
        )
        tokens = sum(max(0, int(char_sum or 0) // 4) for _, _, char_sum in role_rows)
        msgs = (
            db.query(func.count(Message.id))
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(Conversation.user_id.in_(matching_user_ids_subq))
            .scalar()
        )
        msgs = int(msgs or 0)

    usd_rate = assumptions.get("llm_usd_per_million_tokens")
    fx = assumptions.get("ils_per_usd")
    cost_usd = _estimated_llm_cost_usd(tokens, usd_rate)
    cost_ils = None
    if cost_usd is not None and fx is not None:
        cost_ils = round(cost_usd * fx, 2)

    catalog_sum = 0
    if user_count > 0:
        for (plan_key,) in db.query(User.current_plan).filter(User.id.in_(matching_user_ids_subq)).all():
            catalog_sum += _plan_catalog_price_ils(plan_key)

    margin_ils = None
    if cost_ils is not None:
        margin_ils = round(catalog_sum - cost_ils, 2)

    return {
        "user_count": user_count,
        "message_count": msgs,
        "estimated_llm_tokens_approx": tokens,
        "estimated_llm_cost_usd": cost_usd,
        "estimated_llm_cost_ils": cost_ils,
        "catalog_list_price_ils_sum_month": catalog_sum,
        "estimated_margin_catalog_minus_llm_ils": margin_ils,
    }


def _aggregate_user_stats(db: Session, user_ids: list[int]) -> dict[int, dict]:
    """Rollups from Conversation/Message. Token estimate ≈ sum(chars)/4 (rough proxy — no billing-meter logs)."""
    out: dict[int, dict] = {uid: _empty_user_agg() for uid in user_ids}
    if not user_ids:
        return out

    conv_counts = (
        db.query(Conversation.user_id, func.count(Conversation.id))
        .filter(Conversation.user_id.in_(user_ids))
        .group_by(Conversation.user_id)
        .all()
    )
    for uid, cnt in conv_counts:
        if uid in out:
            out[uid]["conversation_count"] = cnt

    role_rows = (
        db.query(
            Conversation.user_id,
            Message.role,
            func.count(Message.id),
            func.coalesce(func.sum(func.length(Message.content)), 0),
        )
        .join(Message, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id.in_(user_ids))
        .group_by(Conversation.user_id, Message.role)
        .all()
    )
    for uid, role, msg_cnt, char_sum in role_rows:
        if uid not in out:
            continue
        char_sum = int(char_sum or 0)
        out[uid]["message_count"] += int(msg_cnt)
        out[uid]["estimated_llm_tokens_approx"] += max(0, char_sum // 4)
        if role == "user":
            out[uid]["user_message_count"] += int(msg_cnt)
        elif role == "assistant":
            out[uid]["assistant_message_count"] += int(msg_cnt)

    last_rows = (
        db.query(Conversation.user_id, func.max(Message.timestamp))
        .join(Message, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id.in_(user_ids))
        .group_by(Conversation.user_id)
        .all()
    )
    for uid, ts in last_rows:
        if uid in out and ts is not None:
            out[uid]["last_activity_at"] = ts.isoformat()

    return out


@router.get("/users")
async def list_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
):
    """
    Paginated user directory with conversation/message counts and a rough LLM token estimate.

    `estimated_llm_tokens_approx` sums ~(characters/4) over **both** user and assistant persisted
    messages (proxy for total text moved through the stack — not Azure billing).

    When env `ADMIN_LLM_USD_PER_MILLION_TOKENS` (and optionally `ADMIN_ILS_PER_USD`) is set,
    each row includes estimated LLM USD cost and catalog-vs-proxy margin in ₪; see `economics_assumptions`.
    """
    q = db.query(User)
    if search and search.strip():
        st = f"%{search.strip()}%"
        q = q.filter(
            or_(
                User.email.ilike(st),
                User.clerk_id.ilike(st),
                User.display_name.ilike(st),
            )
        )

    total = q.count()
    matching_ids_sq = q.with_entities(User.id).subquery()
    assumptions = economics_assumptions()
    directory_totals = _aggregate_directory_totals(
        db, matching_ids_sq, user_count=total, assumptions=assumptions
    )

    users = q.order_by(User.created_at.desc()).offset(max(skip, 0)).limit(min(max(limit, 1), 200)).all()
    ids = [u.id for u in users]
    agg = _aggregate_user_stats(db, ids)
    coupon_users = _users_with_active_coupon(db, ids)

    rows = []
    for u in users:
        a = agg.get(u.id, _empty_user_agg())
        econ = _economics_row(
            tokens_approx=int(a.get("estimated_llm_tokens_approx") or 0),
            plan_key=u.current_plan,
            has_active_coupon=u.id in coupon_users,
            assumptions=assumptions,
        )
        rows.append(
            {
                "id": u.id,
                "clerk_id": u.clerk_id,
                "email": u.email,
                "display_name": u.display_name,
                "gender": u.gender,
                "current_plan": (u.current_plan or "basic").strip() or "basic",
                "is_admin": bool(u.is_admin),
                "stripe_customer_id": bool(u.stripe_customer_id),
                "created_at": u.created_at.isoformat() if u.created_at else None,
                **a,
                **econ,
            }
        )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "economics_assumptions": assumptions,
        "directory_totals": directory_totals,
        "users": rows,
    }


@router.get("/users/{user_id}")
async def get_user_detail(user_id: int, db: Session = Depends(get_db)):
    """Single user profile plus conversations and recent billing-period usage rows."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    agg = _aggregate_user_stats(db, [user_id]).get(user_id, _empty_user_agg())
    assumptions = economics_assumptions()
    coupon_users = _users_with_active_coupon(db, [user_id])
    econ = _economics_row(
        tokens_approx=int(agg.get("estimated_llm_tokens_approx") or 0),
        plan_key=user.current_plan,
        has_active_coupon=user_id in coupon_users,
        assumptions=assumptions,
    )

    conversations = (
        db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).all()
    )
    conv_payload = []
    for c in conversations:
        mc = (
            db.query(Message.role, func.count(Message.id), func.coalesce(func.sum(func.length(Message.content)), 0))
            .filter(Message.conversation_id == c.id)
            .group_by(Message.role)
            .all()
        )
        by_role = {role: {"count": cnt, "chars": int(chars or 0)} for role, cnt, chars in mc}
        conv_payload.append(
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "current_phase": c.current_phase,
                "bsd_step": (c.v2_state or {}).get("current_step") if isinstance(c.v2_state, dict) else None,
                "messages_total": sum(r["count"] for r in by_role.values()),
                "by_role": by_role,
            }
        )

    usage_history = (
        db.query(UsageRecord)
        .filter(UsageRecord.user_id == user_id)
        .order_by(UsageRecord.period_start.desc())
        .limit(12)
        .all()
    )

    return {
        "economics_assumptions": assumptions,
        "economics_per_user": econ,
        "user": {
            "id": user.id,
            "clerk_id": user.clerk_id,
            "email": user.email,
            "display_name": user.display_name,
            "gender": user.gender,
            "current_plan": user.current_plan or "basic",
            "is_admin": bool(user.is_admin),
            "preferences_keys": list((user.preferences or {}).keys()) if isinstance(user.preferences, dict) else [],
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "aggregates": agg,
        "conversations": conv_payload,
        "usage_records": [
            {
                "period_start": ur.period_start.isoformat(),
                "period_end": ur.period_end.isoformat(),
                "messages_used": ur.messages_used,
                "speech_minutes_used": ur.speech_minutes_used,
            }
            for ur in usage_history
        ],
    }


