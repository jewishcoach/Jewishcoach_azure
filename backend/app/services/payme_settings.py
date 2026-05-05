"""PayMe gateway configuration — secrets only via environment (Azure App Service / local .env)."""

from __future__ import annotations

import os


def payme_api_key() -> str:
    """Merchant API key from PayMe (dashboard). Never commit real values."""
    return (os.getenv("PAYME_API_KEY") or "").strip()


def payme_api_base_url() -> str:
    """Payments API base URL (sandbox vs production) — see PayMe docs."""
    return (os.getenv("PAYME_PAYMENTS_API_BASE") or "").strip().rstrip("/")


def payme_webhook_secret() -> str:
    """Optional signing secret for inbound PayMe webhooks, if provided."""
    return (os.getenv("PAYME_WEBHOOK_SECRET") or "").strip()


def payme_is_ready_for_requests() -> bool:
    """True when API key and base URL are both set (minimal gate before HTTP calls)."""
    return bool(payme_api_key() and payme_api_base_url())
