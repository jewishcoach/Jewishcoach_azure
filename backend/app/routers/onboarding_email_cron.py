"""
Internal cron-style trigger for onboarding email dispatch (no Clerk JWT).

Set ONBOARDING_EMAIL_CRON_SECRET on the App Service and call from Azure Logic App,
GitHub Actions schedule, or similar — header X-Onboarding-Email-Cron-Secret must match.
"""

from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.onboarding_email_runtime import process_due_onboarding_emails

router = APIRouter(prefix="/api/internal/onboarding-email", tags=["Internal onboarding email"])


def _verify_cron_secret(header_secret: str | None) -> None:
    expected = (os.getenv("ONBOARDING_EMAIL_CRON_SECRET") or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="ONBOARDING_EMAIL_CRON_SECRET is not set on the server",
        )
    got = (header_secret or "").strip()
    if not got or len(got) != len(expected):
        raise HTTPException(status_code=403, detail="Invalid cron secret")
    if not hmac.compare_digest(got.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Invalid cron secret")


@router.post("/process-due")
def cron_process_due(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    x_onboarding_email_cron_secret: str | None = Header(None, alias="X-Onboarding-Email-Cron-Secret"),
):
    _verify_cron_secret(x_onboarding_email_cron_secret)
    return process_due_onboarding_emails(db, limit=limit)
