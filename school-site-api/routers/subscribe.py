"""Email subscription for blog newsletter."""

from __future__ import annotations

import os
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_admin

router = APIRouter(tags=["subscribe"])

DATABASE_URL = os.environ.get("DATABASE_URL", "")

SUBSCRIBE_SCHEMA = """
CREATE TABLE IF NOT EXISTS email_subscribers (
    email TEXT PRIMARY KEY,
    subscribed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    source TEXT NOT NULL DEFAULT 'blog'
);
"""

_initialized = False


def _init_table():
    global _initialized
    if _initialized or not DATABASE_URL:
        return
    from psycopg_pool import ConnectionPool
    pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=2, open=True)
    with pool.connection() as conn:
        conn.execute(SUBSCRIBE_SCHEMA)
        conn.commit()
    pool.close()
    _initialized = True


def _get_pool():
    import db
    return db._get_pool()


class SubscribeRequest(BaseModel):
    email: str


class SubscribeResponse(BaseModel):
    ok: bool
    message: str = ""


@router.post("/api/subscribe", response_model=SubscribeResponse)
async def subscribe(body: SubscribeRequest):
    _init_table()

    email = body.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return SubscribeResponse(ok=False, message="כתובת מייל לא תקינה")

    if not DATABASE_URL:
        return SubscribeResponse(ok=True, message="נרשמת בהצלחה")

    try:
        with _get_pool().connection() as conn:
            conn.execute(
                "INSERT INTO email_subscribers (email) VALUES (%s) ON CONFLICT (email) DO UPDATE SET active = TRUE",
                (email,),
            )
            conn.commit()
    except Exception:
        return SubscribeResponse(ok=False, message="שגיאה, נסה שוב")

    return SubscribeResponse(ok=True, message="נרשמת בהצלחה")


@router.get("/api/unsubscribe")
async def unsubscribe(email: str):
    if DATABASE_URL:
        try:
            with _get_pool().connection() as conn:
                conn.execute("UPDATE email_subscribers SET active = FALSE WHERE email = %s", (email.lower(),))
                conn.commit()
        except Exception:
            pass
    return {"ok": True, "message": "הוסרת מרשימת התפוצה"}


@router.get("/api/admin/content/subscribers")
async def list_subscribers(_=Depends(require_admin)):
    if not DATABASE_URL:
        return {"subscribers": [], "total": 0}

    with _get_pool().connection() as conn:
        cur = conn.execute("SELECT email, subscribed_at, source FROM email_subscribers WHERE active = TRUE ORDER BY subscribed_at DESC")
        rows = [{"email": r[0], "subscribed_at": r[1].isoformat(), "source": r[2]} for r in cur.fetchall()]
    return {"subscribers": rows, "total": len(rows)}
