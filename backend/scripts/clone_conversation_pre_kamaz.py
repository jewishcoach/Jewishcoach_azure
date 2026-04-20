#!/usr/bin/env python3
"""
Clone a BSD v2 conversation up to (and not including) the first assistant turn in S12,
so the trainee can continue with updated KaMaZ prompts without replaying from S0.

Usage (from repo root or backend/):
  python3 scripts/clone_conversation_pre_kamaz.py --db coaching_azure.db --source-id 170
  python3 scripts/clone_conversation_pre_kamaz.py --db coaching.db --source-id 170 --dry-run

Requires: SQLite conversations + messages tables (same schema as production).
"""
from __future__ import annotations

import argparse
import copy
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _first_s12_coach_index(messages: List[Dict[str, Any]]) -> Optional[int]:
    for i, m in enumerate(messages):
        if m.get("sender") != "coach":
            continue
        ins = m.get("internal_state") or {}
        if ins.get("current_step") == "S12":
            return i
    return None


def _trim_v2_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep all turns before the first coach message that advanced to S12."""
    idx = _first_s12_coach_index(messages)
    if idx is None:
        return list(messages)
    return messages[:idx]


def _last_db_message_id_before_s12(cur: sqlite3.Cursor, conversation_id: int) -> Optional[int]:
    cur.execute(
        """
        SELECT MIN(id) FROM messages
        WHERE conversation_id = ? AND role = 'assistant'
          AND json_extract(meta, '$.phase') = 'S12'
        """,
        (conversation_id,),
    )
    row = cur.fetchone()
    first_s12 = row[0]
    if first_s12 is None:
        return None
    cur.execute(
        "SELECT MAX(id) FROM messages WHERE conversation_id = ? AND id < ?",
        (conversation_id, first_s12),
    )
    return cur.fetchone()[0]


def _build_trimmed_v2_state(source_state: Dict[str, Any], new_conv_id: int, user_id: int) -> Dict[str, Any]:
    msgs = source_state.get("messages") or []
    trimmed = _trim_v2_messages(msgs)
    if not trimmed:
        raise ValueError("Trimmed v2_state has no messages")

    last_coach = None
    for m in reversed(trimmed):
        if m.get("sender") == "coach":
            last_coach = m
            break
    if not last_coach:
        raise ValueError("No coach message in trimmed history")

    ins = last_coach.get("internal_state") or {}
    cd = copy.deepcopy(ins.get("collected_data") or source_state.get("collected_data") or {})
    cd["forces"] = {"source": [], "nature": []}
    cd["offer_trait_picker"] = False

    new_state = copy.deepcopy(source_state)
    new_state["conversation_id"] = str(new_conv_id)
    new_state["user_id"] = str(user_id)
    new_state["messages"] = trimmed
    new_state["current_step"] = "S11"
    new_state["collected_data"] = cd
    new_state["trait_picker_tool_sent"] = False
    new_state["saturation_score"] = float(ins.get("saturation_score") or source_state.get("saturation_score") or 0.5)
    if "stage_saturation" in ins:
        new_state["stage_saturation"] = copy.deepcopy(ins["stage_saturation"])
    if "gate_status" in ins:
        new_state["gate_status"] = copy.deepcopy(ins["gate_status"])
    return new_state


def main() -> int:
    ap = argparse.ArgumentParser(description="Clone conversation up to before KaMaZ (S12) coach turn.")
    ap.add_argument(
        "--db",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "coaching_azure.db",
        help="Path to SQLite DB (default: backend/coaching_azure.db)",
    )
    ap.add_argument("--source-id", type=int, required=True, help="Source conversation id")
    ap.add_argument("--user-id", type=int, default=None, help="Owner user_id (default: same as source)")
    ap.add_argument("--title", type=str, default=None, help="Title for new conversation")
    ap.add_argument("--dry-run", action="store_true", help="Print plan only, no INSERT")
    args = ap.parse_args()

    if not args.db.is_file():
        raise SystemExit(f"DB not found: {args.db}")

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id, user_id, title, v2_state FROM conversations WHERE id = ?", (args.source_id,))
    src = cur.fetchone()
    if not src:
        raise SystemExit(f"Source conversation {args.source_id} not found")
    if not src["v2_state"]:
        raise SystemExit("Source has no v2_state (not a V2 conversation)")

    user_id = int(args.user_id or src["user_id"])
    last_mid = _last_db_message_id_before_s12(cur, args.source_id)
    if last_mid is None:
        raise SystemExit("Could not find S12 boundary (no assistant S12 message?)")

    cur.execute(
        "SELECT id, role, content, timestamp, meta FROM messages WHERE conversation_id = ? AND id <= ? ORDER BY id",
        (args.source_id, last_mid),
    )
    rows = cur.fetchall()
    source_state = json.loads(src["v2_state"]) if isinstance(src["v2_state"], str) else dict(src["v2_state"])
    trimmed_v2 = _trim_v2_messages(source_state.get("messages") or [])
    if len(trimmed_v2) != len(rows):
        raise SystemExit(
            f"Mismatch: trimmed v2 has {len(trimmed_v2)} messages but DB has {len(rows)} rows "
            f"(source {args.source_id}). Abort."
        )

    title = args.title or f"המשך לפני כמ״ז (משיחה {args.source_id})"
    now = datetime.now(timezone.utc)

    print(f"Source conversation: {args.source_id} (user {src['user_id']})")
    print(f"New owner user_id: {user_id}")
    print(f"Messages to copy: {len(rows)} (last message id {last_mid})")
    print(f"v2_state messages after trim: {len(trimmed_v2)}")
    print(f"New title: {title}")

    if args.dry_run:
        print("Dry run — no changes.")
        return 0

    cur.execute(
        """
        INSERT INTO conversations (user_id, title, created_at, updated_at, current_phase, phase_history, v2_state)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            title,
            now.isoformat(),
            now.isoformat(),
            "S11",
            json.dumps([], ensure_ascii=False),
            "{}",  # placeholder; SQLite accepts str
        ),
    )
    new_id = cur.lastrowid

    new_state = _build_trimmed_v2_state(source_state, new_conv_id=new_id, user_id=user_id)

    ts = now
    for r in rows:
        meta = r["meta"]
        if isinstance(meta, dict):
            meta = json.dumps(meta, ensure_ascii=False)
        cur.execute(
            """
            INSERT INTO messages (conversation_id, role, content, timestamp, meta)
            VALUES (?, ?, ?, ?, ?)
            """,
            (new_id, r["role"], r["content"], ts.isoformat(), meta or "{}"),
        )
        ts += timedelta(milliseconds=3)

    cur.execute(
        "UPDATE conversations SET v2_state = ?, updated_at = ?, current_phase = ? WHERE id = ?",
        (json.dumps(new_state, ensure_ascii=False), ts.isoformat(), "S11", new_id),
    )
    conn.commit()
    conn.close()

    print(f"\nCreated conversation id={new_id}")
    print("Open this conversation in the app (same user account) and send the next message to open S12 with the new prompts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
