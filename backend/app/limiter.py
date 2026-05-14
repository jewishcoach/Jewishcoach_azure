"""Rate limiter instance for SlowAPI.
Uses X-Forwarded-For when behind Azure/proxy to get real client IP.

By default limits live in process memory (each Gunicorn worker / instance has its own
counters). For accurate limits under multiple workers or scaled App Service instances,
point storage at Redis via ``RATELIMIT_STORAGE_URL`` (SlowAPI) or ``REDIS_URL`` (alias).

Azure Cache for Redis typically uses TLS on port 6380, for example:
    rediss://:YOUR_ACCESS_KEY@your-cache.redis.cache.windows.net:6380/0
"""
import os

from slowapi import Limiter
from starlette.requests import Request


def get_client_ip(request: Request) -> str:
    """Get client IP, respecting X-Forwarded-For when behind proxy (Azure)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP is the original client; rest are proxies
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


_redis_uri = (
    os.getenv("RATELIMIT_STORAGE_URL", "").strip()
    or os.getenv("REDIS_URL", "").strip()
    or None
)

limiter = Limiter(key_func=get_client_ip, storage_uri=_redis_uri)
