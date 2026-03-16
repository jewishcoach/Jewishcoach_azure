"""Rate limiter instance for SlowAPI.
Uses X-Forwarded-For when behind Azure/proxy to get real client IP.
"""
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


limiter = Limiter(key_func=get_client_ip)
