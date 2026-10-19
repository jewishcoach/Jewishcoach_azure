import os

from fastapi import Header, HTTPException


INTERNAL_KEY = os.environ.get("API_INTERNAL_KEY", "dev-key-change-me")


async def require_admin(x_internal_key: str = Header(...)):
    if x_internal_key != INTERNAL_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
