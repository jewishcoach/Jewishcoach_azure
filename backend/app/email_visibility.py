"""Normalize email for client-visible APIs — hide Clerk placeholder inboxes."""

from __future__ import annotations

from typing import Optional


def normalize_public_email(email: Optional[str]) -> Optional[str]:
    """
    Return email for display/API responses, or None if it is a Clerk synthetic address.

    Backend stores ``{clerk_id}@clerk.temp`` when JWT has no real email (see dependencies).
    """
    if email is None:
        return None
    if not isinstance(email, str):
        return None
    stripped = email.strip()
    if not stripped:
        return None
    lower = stripped.lower()
    if lower.endswith("@clerk.temp") or "@clerk.accounts." in lower:
        return None
    return stripped
