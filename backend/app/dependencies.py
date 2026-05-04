from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import Depends, HTTPException, Header
from jose import jwt as jose_jwt
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .database import get_db, utc_now
from .models import User

import json
import os
import urllib.error
import urllib.parse
import urllib.request

# Optional: JWT verification with Clerk JWKS (set CLERK_JWKS_URL for production)
_jwks_client = None


def _get_jwks_client():
    """Lazy-init PyJWKClient when CLERK_JWKS_URL is set."""
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client
    url = os.getenv("CLERK_JWKS_URL", "").strip()
    if not url:
        return None
    try:
        import jwt
        _jwks_client = jwt.PyJWKClient(url, cache_keys=True)
        return _jwks_client
    except Exception:
        return None


def _verify_clerk_token(token: str) -> dict | None:
    """
    Verify Clerk JWT with JWKS if CLERK_JWKS_URL is set.
    Returns payload on success, None if verification skipped (fallback to unverified).
    """
    client = _get_jwks_client()
    if not client:
        return None
    try:
        import jwt
        header = jwt.get_unverified_header(token)
        key = client.get_signing_key(header.get("kid"))
        payload = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_azp": False},
        )
        return payload
    except Exception:
        raise


def _extract_email(payload: dict) -> str | None:
    """Best-effort email extraction from Clerk JWT payloads."""
    # Common direct keys
    for key in ("email", "email_address", "primary_email_address", "primary_email", "emailAddress"):
        value = payload.get(key)
        if isinstance(value, str) and "@" in value:
            return value

    # Nested primary object (some Clerk / custom templates)
    primary = payload.get("primary_email_address")
    if isinstance(primary, dict):
        addr = primary.get("email_address")
        if isinstance(addr, str) and "@" in addr:
            return addr

    # Clerk often uses email_addresses with primary_email_address_id
    email_addresses = payload.get("email_addresses")
    if isinstance(email_addresses, list) and email_addresses:
        primary_id = payload.get("primary_email_address_id")
        if primary_id:
            for item in email_addresses:
                if isinstance(item, dict) and item.get("id") == primary_id:
                    addr = item.get("email_address")
                    if isinstance(addr, str) and addr:
                        return addr
        # Fallback to first item
        first = email_addresses[0]
        if isinstance(first, dict):
            addr = first.get("email_address")
            if isinstance(addr, str) and addr:
                return addr
        if isinstance(first, str) and first:
            return first

    # Custom claims URLs (Clerk JWT templates sometimes use namespaced keys)
    for key, value in payload.items():
        if not isinstance(key, str) or "email" not in key.lower():
            continue
        if isinstance(value, str) and "@" in value:
            return value

    return None


_CLERK_PRIMARY_EMAIL_CACHE: dict[str, str] = {}


def _normalized_email_for_admin_match(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.strip().lower()


def _admin_email_allowlist_normalized() -> set[str]:
    raw = (os.getenv("ADMIN_EMAIL", "") or "").strip()
    out: set[str] = set()
    for part in raw.split(","):
        n = _normalized_email_for_admin_match(part.strip())
        if n:
            out.add(n)
    return out


def _admin_clerk_id_allowlist() -> set[str]:
    raw = (os.getenv("ADMIN_CLERK_IDS", "") or "").strip()
    ids: set[str] = set()
    for x in raw.split(","):
        s = x.strip().strip('"').strip("'").strip()
        if s:
            ids.add(s)
    return ids


def _should_grant_admin(clerk_id: str, resolved_email: str | None) -> bool:
    """
    Admin if Clerk user id is listed in ADMIN_CLERK_IDS, or resolved email matches ADMIN_EMAIL
    (comma-separated, case-insensitive). JWT often omits email — use resolve + optional Clerk API.
    """
    if clerk_id and clerk_id in _admin_clerk_id_allowlist():
        return True
    allow = _admin_email_allowlist_normalized()
    if not allow:
        return False
    em = _normalized_email_for_admin_match(resolved_email)
    return bool(em and em in allow)


def _pick_email_from_clerk_user_body(body: dict[str, Any]) -> str | None:
    """Best-effort inbox from Clerk GET /v1/users/{id} JSON (shape varies slightly)."""
    pe = body.get("primary_email_address")
    if isinstance(pe, dict):
        addr = pe.get("email_address") or pe.get("emailAddress")
        if isinstance(addr, str) and "@" in addr:
            return addr
    primary_id = body.get("primary_email_address_id")
    emails = body.get("email_addresses") or []
    chosen: str | None = None
    if isinstance(emails, list) and primary_id:
        for ea in emails:
            if isinstance(ea, dict) and ea.get("id") == primary_id:
                addr = ea.get("email_address") or ea.get("emailAddress")
                if isinstance(addr, str) and "@" in addr:
                    chosen = addr
                    break
    if chosen is None and isinstance(emails, list):
        for ea in emails:
            if isinstance(ea, dict):
                addr = ea.get("email_address") or ea.get("emailAddress")
                if isinstance(addr, str) and "@" in addr:
                    chosen = addr
                    break
    return chosen


def _fetch_clerk_primary_email(clerk_id: str) -> str | None:
    """Backend API: needs CLERK_SECRET_KEY (sk_live_ / sk_test_). Cached per process."""
    if clerk_id in _CLERK_PRIMARY_EMAIL_CACHE:
        return _CLERK_PRIMARY_EMAIL_CACHE[clerk_id]
    secret = os.getenv("CLERK_SECRET_KEY", "").strip()
    if not secret or not clerk_id:
        return None
    safe_id = urllib.parse.quote(clerk_id, safe="")
    url = f"https://api.clerk.com/v1/users/{safe_id}"
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {secret}"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode(errors="replace")[:400]
        except Exception:
            pass
        print(f"⚠️ [AUTH] Clerk user lookup HTTP {e.code} for {clerk_id}: {detail or e.reason}")
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as e:
        print(f"⚠️ [AUTH] Clerk user lookup failed for {clerk_id}: {type(e).__name__}: {e}")
        return None
    if not isinstance(body, dict):
        return None
    chosen = _pick_email_from_clerk_user_body(body)
    if chosen:
        _CLERK_PRIMARY_EMAIL_CACHE[clerk_id] = chosen
        print(f"✅ [AUTH] Resolved primary email from Clerk API for {clerk_id}")
        return chosen
    return None


def warm_clerk_email_cache_for_users(users: list[Any]) -> None:
    """
    Pre-fetch Clerk primary emails for directory rows that still lack a real inbox in DB.

    Without this, /admin/users hits Clerk sequentially once per row (slow; looks like 'no emails').
    Safe to call repeatedly; uses per-process cache and skips users who already have public emails in DB.
    """
    need: list[str] = []
    seen: set[str] = set()
    for u in users:
        db = (getattr(u, "email", None) or "").strip()
        if db and "@clerk.temp" not in db and "@" in db:
            continue
        cid = (getattr(u, "clerk_id", None) or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        need.append(cid)
    if not need:
        return
    workers = min(12, max(1, len(need)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_fetch_clerk_primary_email, need))


def _resolve_primary_email(
    jwt_email: str | None,
    clerk_id: str,
    existing_db_email: str | None,
) -> str | None:
    """Prefer JWT email, then non-placeholder DB row, then Clerk Backend API."""
    je = jwt_email.strip() if isinstance(jwt_email, str) else None
    if je and "@" in je:
        return je
    db = (existing_db_email or "").strip()
    if db and "@clerk.temp" not in db and "@" in db:
        return db
    return _fetch_clerk_primary_email(clerk_id)


def resolve_email_from_db_and_clerk(clerk_id: str, db_email: str | None) -> str | None:
    """
    Real inbox for admin/support: prefer non-placeholder DB row, else Clerk Backend API.
    Requires CLERK_SECRET_KEY for API fallback (same as login resolution).
    """
    cid = (clerk_id or "").strip()
    if not cid:
        return None
    return _resolve_primary_email(None, cid, db_email)


def admin_diagnosis_for_request(authorization: str | None, user: User) -> dict:
    """
    Safe troubleshooting payload for the signed-in user only (no secrets).
    Helps debug missing admin UI when JWT omits email / Clerk API issues.
    """
    out: dict = {
        "db_user_id": user.id,
        "db_clerk_id": user.clerk_id,
        "db_email_raw": user.email,
        "db_is_admin": bool(user.is_admin),
        "env_ADMIN_EMAIL_set": bool(os.getenv("ADMIN_EMAIL", "").strip()),
        "env_ADMIN_CLERK_IDS_set": bool(os.getenv("ADMIN_CLERK_IDS", "").strip()),
        "env_CLERK_SECRET_KEY_set": bool(os.getenv("CLERK_SECRET_KEY", "").strip()),
    }
    if not authorization or not authorization.startswith("Bearer "):
        out["jwt_error"] = "missing_bearer"
        return out
    token = authorization.replace("Bearer ", "", 1)
    try:
        payload = jose_jwt.get_unverified_claims(token)
    except Exception as e:
        out["jwt_error"] = f"decode_failed:{type(e).__name__}"
        return out
    clerk_sub = payload.get("sub")
    jwt_email = _extract_email(payload)
    resolved = _resolve_primary_email(jwt_email, clerk_sub or "", user.email)
    out.update(
        {
            "jwt_sub": clerk_sub,
            "jwt_matches_db_clerk": bool(clerk_sub and user.clerk_id == clerk_sub),
            "jwt_has_email_claim": bool(jwt_email),
            "resolved_email_for_admin_check": resolved,
            "computed_should_be_admin": _should_grant_admin(clerk_sub or "", resolved),
            "admin_email_allowlist_count": len(_admin_email_allowlist_normalized()),
            "admin_clerk_id_allowlist_count": len(_admin_clerk_id_allowlist()),
        }
    )
    return out


async def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
    origin: str = Header(None)
) -> User:
    """
    Extract Clerk user from JWT token and sync to database.
    MVP: Simple extraction without full verification.
    
    DEMO MODE: If request comes from tunnel domain (*.lhr.life, *.ngrok-free.app)
    and ALLOW_DEMO_MODE=true, create/return a demo user for testing.
    """
    # Log every request
    print(f"🔍 [AUTH] Request received - Origin: {origin if origin else 'NOT SET'}, Auth: {authorization[:30] if authorization else 'NOT SET'}...")
    
    # Demo mode for tunnel testing (TEMPORARY) - only for dev tunnels, NOT production
    # azurestaticapps.net is production frontend - users there must use real Clerk auth
    # Default false: production-safe. Set ALLOW_DEMO_MODE=true for local tunnel testing only.
    allow_demo = os.getenv("ALLOW_DEMO_MODE", "false").lower() == "true"
    is_tunnel_domain = origin and any(domain in origin for domain in ['.lhr.life', '.ngrok-free.app', '.localhost.run'])
    
    print(f"🔍 [AUTH] allow_demo={allow_demo}, is_tunnel_domain={is_tunnel_domain}")
    
    if allow_demo and is_tunnel_domain:
        print(f"🎭 [DEMO MODE] Request from tunnel domain: {origin}")
        
        # Get or create demo user
        demo_clerk_id = "demo_user_tunnel"
        user = db.query(User).filter(User.clerk_id == demo_clerk_id).first()
        
        if not user:
            user = User(
                clerk_id=demo_clerk_id,
                email="demo@tunnel.test",
                display_name="Demo User",
                is_admin=False,
                created_at=utc_now()
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ [DEMO MODE] Created demo user for tunnel testing")
        
        return user
    
    # Normal Clerk authentication
    print(f"🔑 [AUTH DEBUG] Authorization header: {authorization[:50] if authorization else 'MISSING'}...")
    
    if not authorization or not authorization.startswith("Bearer "):
        print(f"❌ [AUTH DEBUG] No valid Bearer token in header")
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    token = authorization.replace("Bearer ", "")
    print(f"🎫 [AUTH DEBUG] JWT token (first 30 chars): {token[:30]}...")
    
    try:
        # Verify with JWKS if CLERK_JWKS_URL is set; otherwise unverified (MVP/dev)
        payload = None
        if _get_jwks_client():
            payload = _verify_clerk_token(token)
        if payload is None:
            payload = jose_jwt.get_unverified_claims(token)
        clerk_id = payload.get("sub")
        print(f"✅ [AUTH DEBUG] Decoded JWT, clerk_id: {clerk_id}")
        jwt_email = _extract_email(payload)
        if jwt_email:
            print(f"✅ [AUTH DEBUG] Email from JWT: {jwt_email[:3]}***")
        else:
            print("⚠️ [AUTH DEBUG] No email claim in JWT — will use DB or Clerk API if configured")

        if not clerk_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
        
        # Sync user to database (upsert)
        user = db.query(User).filter(User.clerk_id == clerk_id).first()

        resolved_email = _resolve_primary_email(jwt_email, clerk_id, user.email if user else None)
        should_be_admin = _should_grant_admin(clerk_id, resolved_email)
        
        if not user:
            # Auto-register new user
            row_email = resolved_email or jwt_email or f"{clerk_id}@clerk.temp"
            user = User(
                clerk_id=clerk_id,
                email=row_email,
                is_admin=should_be_admin,
                created_at=utc_now()
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            try:
                from .services.onboarding_email_runtime import maybe_enqueue_default_sequence

                maybe_enqueue_default_sequence(db, user)
            except Exception as oe:
                print(f"⚠️ [OnboardingEmail] enqueue after signup failed: {type(oe).__name__}: {oe}")
            
            if should_be_admin:
                print(f"✅ Admin user created: clerk_id={clerk_id} email={resolved_email or jwt_email}")
        else:
            updated = False

            # Prefer real email from JWT, Clerk API, or keep existing non-placeholder
            if resolved_email and "@" in resolved_email and user.email != resolved_email:
                user.email = resolved_email
                updated = True

            if should_be_admin and not user.is_admin:
                user.is_admin = True
                updated = True
                print(f"✅ Admin user promoted: clerk_id={clerk_id} email={resolved_email}")

            if updated:
                db.commit()
        
        return user

    except HTTPException:
        raise
    except OperationalError as e:
        print(f"❌ [AUTH DEBUG] Database error (not a JWT issue): {e}")
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")
    except Exception as e:
        print(f"❌ [AUTH DEBUG] JWT decode failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify user has admin privileges.
    Raises 403 if not admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return current_user

