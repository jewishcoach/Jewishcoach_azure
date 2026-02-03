from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from jose import jwt
from .database import get_db
from .models import User
from datetime import datetime
import os


def _extract_email(payload: dict) -> str | None:
    """Best-effort email extraction from Clerk JWT payloads."""
    # Common direct keys
    for key in ("email", "email_address", "primary_email_address", "primary_email", "emailAddress"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

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

    return None

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
    
    # Demo mode for tunnel testing (TEMPORARY)
    allow_demo = os.getenv("ALLOW_DEMO_MODE", "true").lower() == "true"
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
                created_at=datetime.utcnow()
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
        # Decode token (unverified for MVP)
        payload = jwt.get_unverified_claims(token)
        clerk_id = payload.get("sub")
        print(f"✅ [AUTH DEBUG] Decoded JWT, clerk_id: {clerk_id}")
        email = _extract_email(payload)
        
        if not clerk_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
        
        # Sync user to database (upsert)
        user = db.query(User).filter(User.clerk_id == clerk_id).first()
        
        if not user:
            # Auto-register new user
            # Check if this email should be an admin
            admin_email = os.getenv("ADMIN_EMAIL")
            is_admin = (email == admin_email) if admin_email else False
            
            user = User(
                clerk_id=clerk_id,
                email=email or f"{clerk_id}@clerk.temp",
                is_admin=is_admin,
                created_at=datetime.utcnow()
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            if is_admin:
                print(f"✅ Admin user created: {email}")
        else:
            # Sync email/admin for existing users
            admin_email = os.getenv("ADMIN_EMAIL")
            should_be_admin = (email == admin_email) if admin_email else False
            updated = False

            if email and user.email.endswith("@clerk.temp"):
                user.email = email
                updated = True

            if should_be_admin and not user.is_admin:
                user.is_admin = True
                updated = True
                print(f"✅ Admin user promoted: {email}")

            if updated:
                db.commit()
        
        return user
        
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

