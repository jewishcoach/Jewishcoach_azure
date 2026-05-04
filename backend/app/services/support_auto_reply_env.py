"""Effective auto-reply flag: DB row + optional SUPPORT_AUTO_REPLY_ENABLED env override."""

from __future__ import annotations

import os

from ..models import SupportCustomerServiceSettings


def effective_auto_reply_enabled(row: SupportCustomerServiceSettings) -> bool:
    """
    Inbound pipeline uses this instead of the raw DB column alone.

    Azure App Service can set SUPPORT_AUTO_REPLY_ENABLED=true|false without opening the admin UI.
    Empty env → follow DB (support_customer_service_settings.auto_reply_enabled).
    """
    raw = (os.getenv("SUPPORT_AUTO_REPLY_ENABLED") or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return bool(getattr(row, "auto_reply_enabled", False))


def support_auto_reply_env_raw() -> str | None:
    v = (os.getenv("SUPPORT_AUTO_REPLY_ENABLED") or "").strip()
    return v if v else None
