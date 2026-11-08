"""
Admin journey dashboard (Nov 2026): where users are in the process, where they stop, which steps take many turns.

Numbers only — the conversation text is never read (the privacy policy: staff access content only for faults,
safety or support). Steps per turn come from the coach message meta ("from" = the step the client answered,
"phase" = the step after the turn, "card" = the card submitted); older messages without "from" fall back to the
previous coach message's phase.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..bsd_v2.stage_intro_schema import MACRO_STAGES
from ..bsd_v2.stage_tool_triggers import pending_card_on_resume
from ..models import Conversation, CoupleMember, Message, ToolResponse, User
from ..routers.billing import active_coupon_messages_limit
from ..schemas.billing import effective_messages_per_month

STEPS = [f"S{i}" for i in range(16)]
STALL_AFTER = timedelta(hours=24)   # no activity for this long and not finished → "stopped here"
IDLE_GAP = timedelta(minutes=30)    # a longer pause between messages is a break, not time spent on the step
LOOP_TURNS = 8                      # this many client turns inside one step = probably stuck (S2 had 12, Nov 1)


def _idx(step: Optional[str]) -> int:
    try:
        return int(str(step or "S0").lstrip("S"))
    except ValueError:
        return 0


def _naive(ts: Optional[datetime]) -> Optional[datetime]:
    return ts.replace(tzinfo=None) if ts and ts.tzinfo else ts


def _pct(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    v = sorted(values)
    return v[min(len(v) - 1, int(round(p * (len(v) - 1))))]


def _where(state: Dict[str, Any], completed: bool) -> Dict[str, Any]:
    """Where the client is now, in screen terms."""
    step = state.get("current_step") or "S0"
    if completed:
        return {"kind": "completed", "step": step}
    if state.get("pending_stage_intro"):
        return {"kind": "stage_intro", "step": step}
    try:
        card = pending_card_on_resume(state)
    except Exception:  # an odd old state must not break the dashboard
        card = None
    if card:
        return {"kind": "card", "step": step, "card": card.get("tool_type")}
    return {"kind": "chat", "step": step}


def compute_journey(db: Session, days: int = 30, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = _naive(now) or datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(days=days) if days and days > 0 else None

    users = db.query(User).all()
    conv_q = db.query(Conversation)
    if since:
        conv_q = conv_q.filter(Conversation.created_at >= since)
    convs = conv_q.all()
    conv_ids = [c.id for c in convs]

    # metadata only — never the message text
    msgs_by_conv: Dict[int, list] = defaultdict(list)
    if conv_ids:
        for cid, role, ts, meta, length in (
            db.query(Message.conversation_id, Message.role, Message.timestamp, Message.meta, func.length(Message.content))
            .filter(Message.conversation_id.in_(conv_ids))
            .order_by(Message.conversation_id, Message.timestamp, Message.id)
        ):
            msgs_by_conv[cid].append((role, _naive(ts), meta or {}, length or 0))
    cards_by_conv: Dict[int, List[str]] = defaultdict(list)
    if conv_ids:
        for cid, tool in db.query(ToolResponse.conversation_id, ToolResponse.tool_type).filter(
                ToolResponse.conversation_id.in_(conv_ids)):
            cards_by_conv[cid].append(tool)
    couple_conv_ids = {cid for (cid,) in db.query(CoupleMember.conversation_id).filter(
        CoupleMember.conversation_id.isnot(None))}

    step_turns: Dict[str, List[int]] = defaultdict(list)      # per step: client turns in each conversation
    step_minutes: Dict[str, List[float]] = defaultdict(list)
    step_latency: Dict[str, List[float]] = defaultdict(list)  # coach response time, seconds
    reached = defaultdict(int)
    here_now = defaultdict(int)
    stalled_here = defaultdict(int)
    loops = defaultdict(int)
    conv_rows: List[Dict[str, Any]] = []
    last_active_by_user: Dict[int, datetime] = {}

    for c in convs:
        state = c.v2_state if isinstance(c.v2_state, dict) else {}
        msgs = msgs_by_conv.get(c.id, [])
        user_turns = sum(1 for m in msgs if m[0] == "user")
        if user_turns == 0:
            continue  # opened during an onboarding the client left
        completed = "commitment_card" in cards_by_conv.get(c.id, [])
        cur = state.get("current_step") or "S0"
        last = max([m[1] for m in msgs if m[1]] + [_naive(c.created_at)])
        stalled = not completed and now - last > STALL_AFTER

        turns = defaultdict(int)
        minutes = defaultdict(float)
        prev_phase, prev_ts = "S0", _naive(c.created_at)
        for role, ts, meta, _len in msgs:
            if role == "assistant":
                step = meta.get("from") or prev_phase
                turns[step] += 1
                t = (meta.get("timing_ms") or {}).get("total")
                if isinstance(t, (int, float)):
                    step_latency[step].append(t / 1000)
                prev_phase = meta.get("phase") or prev_phase
            if ts and prev_ts and ts >= prev_ts and ts - prev_ts <= IDLE_GAP:
                minutes[prev_phase if role == "user" else (meta.get("from") or prev_phase)] += (ts - prev_ts).total_seconds() / 60
            prev_ts = ts or prev_ts
        for step, n in turns.items():
            step_turns[step].append(n)
            if n >= LOOP_TURNS:
                loops[step] += 1
        for step, m in minutes.items():
            step_minutes[step].append(m)

        top_step = max(turns, key=turns.get) if turns else cur
        for s in STEPS:
            if _idx(s) <= _idx(cur):
                reached[s] += 1
        if not completed:
            here_now[cur] += 1
            if stalled:
                stalled_here[cur] += 1
        prev = last_active_by_user.get(c.user_id)
        last_active_by_user[c.user_id] = max(prev, last) if prev else last
        conv_rows.append({
            "id": c.id,
            "user_id": c.user_id,
            "created_at": _naive(c.created_at).isoformat() if c.created_at else None,
            "last_active": last.isoformat(),
            "step": cur,
            "where": _where(state, completed),
            "status": "completed" if completed else "stalled" if stalled else "active",
            "user_turns": user_turns,
            "most_turns_step": top_step,
            "most_turns": turns.get(top_step, 0),
            "couple": c.id in couple_conv_ids or bool(state.get("couple")),
            "cards": len(cards_by_conv.get(c.id, [])),
        })

    started = len(conv_rows)
    done = [r for r in conv_rows if r["status"] == "completed"]
    steps_out = []
    for s in ["S0"] + STEPS[2:]:  # S0 = the opening message (onboarding line → first coach reply)
        t = step_turns.get(s, [])
        mins = step_minutes.get(s, [])
        lat = step_latency.get(s, [])
        steps_out.append({
            "step": s,
            "reached": reached.get(s, 0),
            "here_now": here_now.get(s, 0),
            "stalled_here": stalled_here.get(s, 0),
            "avg_turns": round(sum(t) / len(t), 1) if t else None,
            "p90_turns": _pct(t, 0.9),
            "loops": loops.get(s, 0),
            "median_minutes": round(median(mins), 1) if mins else None,
            "latency_p50": round(_pct(lat, 0.5), 1) if lat else None,
            "latency_p90": round(_pct(lat, 0.9), 1) if lat else None,
        })
    macro_out = [{
        "id": m["id"], "title_he": m["title_he"], "first_step": m["s_start"] if m["s_start"] != "S0" else "S2",
        "reached": reached.get(m["s_start"] if m["s_start"] != "S0" else "S2", 0),
    } for m in MACRO_STAGES]

    convs_per_user = defaultdict(int)
    latest_by_user: Dict[int, Dict[str, Any]] = {}
    for r in sorted(conv_rows, key=lambda r: r["last_active"]):
        convs_per_user[r["user_id"]] += 1
        latest_by_user[r["user_id"]] = r
    used = dict(db.query(Conversation.user_id, func.count(Message.id))
                .join(Message, Message.conversation_id == Conversation.id)
                .filter(Message.role == "user").group_by(Conversation.user_id).all())
    user_rows = []
    for u in users:
        limit = effective_messages_per_month(email=u.email, plan_key=u.current_plan, clerk_id=u.clerk_id,
                                             coupon_messages_limit=active_coupon_messages_limit(db, u),
                                             is_admin=bool(u.is_admin))
        latest = latest_by_user.get(u.id)
        la = last_active_by_user.get(u.id)
        user_rows.append({
            "id": u.id,
            "name": u.display_name,
            "email": u.email if u.email and not u.email.endswith("@clerk.temp") else None,
            "gender": u.gender,
            "plan": (u.current_plan or "basic"),
            "created_at": _naive(u.created_at).isoformat() if u.created_at else None,
            "last_active": la.isoformat() if la else None,
            "conversations": convs_per_user.get(u.id, 0),
            "messages_used": int(used.get(u.id, 0)),
            "messages_limit": limit,
            "latest": {"step": latest["step"], "where": latest["where"], "status": latest["status"]} if latest else None,
        })
    user_rows.sort(key=lambda r: r["last_active"] or "", reverse=True)

    def active_within(delta: timedelta) -> int:
        return sum(1 for t in last_active_by_user.values() if now - t <= delta)

    total_turns_done = [r["user_turns"] for r in done]
    return {
        "generated_at": now.isoformat(),
        "days": days,
        "overview": {
            "users_total": len(users),
            "users_new": sum(1 for u in users if since is None or (u.created_at and _naive(u.created_at) >= since)),
            "active_24h": active_within(timedelta(hours=24)),
            "active_7d": active_within(timedelta(days=7)),
            "conversations": started,
            "completed": len(done),
            "completion_rate": round(100 * len(done) / started, 1) if started else None,
            "stalled": sum(1 for r in conv_rows if r["status"] == "stalled"),
            "couple_conversations": sum(1 for r in conv_rows if r["couple"]),
            "median_turns_to_complete": median(total_turns_done) if total_turns_done else None,
        },
        "macro_funnel": macro_out,
        "steps": steps_out,
        "users": user_rows,
        "conversations": sorted(conv_rows, key=lambda r: r["last_active"], reverse=True)[:100],
        "thresholds": {"stall_hours": STALL_AFTER.total_seconds() / 3600, "loop_turns": LOOP_TURNS},
    }
