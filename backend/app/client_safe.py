"""
Safe responses for untrusted HTTP clients.

Default: no exception text, no stack hints, no infra enumeration in public JSON.
Enable verbose API responses only in trusted dev: ALLOW_PUBLIC_ERROR_DETAILS=true
"""

from __future__ import annotations

import os
from typing import Any


def allow_public_error_details() -> bool:
    """When True, OpenAPI/docs and some endpoints may expose extra diagnostic text."""
    return os.getenv("ALLOW_PUBLIC_ERROR_DETAILS", "false").lower() == "true"


def client_error_detail(public_message: str, exc: BaseException | None = None) -> str:
    """HTTP ``detail`` string safe for end users (and scanners)."""
    if allow_public_error_details() and exc is not None:
        return f"{public_message} ({type(exc).__name__}: {exc})"
    return public_message


def public_json(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Minimal public payload; full diagnostics only when ALLOW_PUBLIC_ERROR_DETAILS."""
    base: dict[str, Any] = {"status": "ok"}
    if allow_public_error_details() and extra:
        base.update(extra)
    return base
