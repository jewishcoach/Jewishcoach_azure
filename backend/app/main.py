from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .limiter import limiter
from .routers import (
    chat,
    speech,
    feedback,
    users,
    journal,
    tools,
    admin,
    billing,
    profile,
    calendar,
    onboarding_email_cron,
    onboarding_intake,
)
from .routers.support_email_inbound import router as support_email_inbound_router
from .routers.support_user_contact import router as support_user_contact_router
from .api import chat_v2, debug_health, version, debug_logs  # BSD V2 + Debug + Version + Logs
import os
from dotenv import load_dotenv

load_dotenv()

import logging

_main_log = logging.getLogger(__name__)


def _configure_app_logging() -> None:
    """Quiet app modules by default; set VERBOSE_HTTP_LOGS=true for auth/chat tracing."""
    verbose = os.getenv("VERBOSE_HTTP_LOGS", "").lower() == "true"
    level = logging.DEBUG if verbose else logging.WARNING
    for name in ("app.dependencies", "app.api.chat_v2", "app.routers.chat"):
        logging.getLogger(name).setLevel(level)


_configure_app_logging()

from .client_safe import allow_public_error_details

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks (runs once per worker process)."""
    try:
        from .database import SessionLocal
        from .services.coupon_bootstrap import ensure_bsd100_coupon

        db = SessionLocal()
        try:
            ensure_bsd100_coupon(db)
        finally:
            db.close()
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "Coupon bootstrap failed at startup (non-fatal); redeem-coupon may fail until DB is ready"
        )
    yield


# Important: do not create DB schema at import-time.
# With multiple Gunicorn workers this can race (especially on SQLite)
# and fail the whole app boot. Schema init is handled in startup.sh once.

_public_docs = allow_public_error_details()

app = FastAPI(
    title="Jewish Coaching API",
    description="AI Coaching platform with RAG and Voice support",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _public_docs else None,
    redoc_url="/redoc" if _public_docs else None,
    openapi_url="/openapi.json" if _public_docs else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Reduce browser-side abuse (clickjacking, MIME sniffing); voice keeps mic on same origin."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "accelerometer=(), camera=(), geolocation=(), microphone=(self), payment=(self)",
    )
    return response

# CORS Configuration
# Support for local development AND Ngrok tunneling.
#
# IMPORTANT: Many environments set CORS_ORIGINS; we always union-in common local dev
# origins because Vite may auto-shift ports (5173 -> 5174) if 5173 is taken.
origins_env = os.getenv("CORS_ORIGINS", "")
origins_list = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
for o in ("http://localhost:5173", "http://localhost:5174"):
    if o not in origins_list:
        origins_list.append(o)

# Azure Static Web Apps - add common deployment URLs (e.g. thankful-forest-*.azurestaticapps.net)
# Production custom domain (HTTPS) — also set CORS_ORIGINS in App Service for any extra origins.
for azure_origin in (
    "https://thankful-forest-049e9550f.1.azurestaticapps.net",
    "https://jewish-coach.azurestaticapps.net",
    "https://jewishcoacher.com",
    "https://www.jewishcoacher.com",
    "https://bsdcoach.com",
    "https://www.bsdcoach.com",
):
    if azure_origin not in origins_list:
        origins_list.append(azure_origin)

# Apex + any subdomain over HTTPS (www., previews, etc.) beyond explicit allow_origins entries.
_JEWISHCOACHER_HTTPS_ORIGIN_REGEX = r"https://([\w-]+\.)*jewishcoacher\.com"

# Default false: allow only CORS_ORIGINS + localhost dev ports. Set ALLOW_TUNNELS=true for ngrok etc.
allow_tunnels = os.getenv("ALLOW_TUNNELS", "false").lower() == "true"

if allow_tunnels:
    # Add regex patterns to allow tunneling services: ngrok, localhost.run, azurestaticapps, etc.
    # Note: Azure Static Web Apps use *.azurestaticapps.net (incl. subdomains like xxx.1.azurestaticapps.net)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list,
        allow_origin_regex=(
            _JEWISHCOACHER_HTTPS_ORIGIN_REGEX
            + r"|https://[^/]+\.(ngrok-free\.app|lhr\.life|localhost\.run|azurestaticapps\.net)"
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    _main_log.info("CORS: Remote tunneling enabled (ngrok, localhost.run, azurestaticapps.net)")
else:
    # Standard CORS for specific origins only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list,
        allow_origin_regex=_JEWISHCOACHER_HTTPS_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _main_log.info("CORS: Configured for %d origins", len(origins_list))

# Include routers
app.include_router(chat.router)  # V1 - Multi-layer architecture
app.include_router(chat_v2.router)  # V2 - Single-agent conversational coach
app.include_router(debug_health.router)  # Debug endpoints
app.include_router(version.router)  # Version check
app.include_router(debug_logs.router)  # Log access
app.include_router(speech.router)
app.include_router(feedback.router)
app.include_router(users.router)
app.include_router(journal.router)
app.include_router(tools.router)
app.include_router(admin.router)
app.include_router(onboarding_email_cron.router)
app.include_router(support_email_inbound_router)
app.include_router(support_user_contact_router)
app.include_router(billing.router)
app.include_router(profile.router)
app.include_router(calendar.router)
app.include_router(onboarding_intake.router)
app.include_router(onboarding_intake.coach_feedback_survey_router)

@app.get("/")
def root():
    if allow_public_error_details():
        return {
            "message": "Jewish Coaching API",
            "status": "running",
            "version": "2.0.1",
            "bsd_version": "v2",
        }
    return {"status": "running"}

@app.get("/health")
def health_check():
    """
    Health check endpoint for Azure App Service.
    Default: minimal signal only. Full internals when ALLOW_PUBLIC_ERROR_DETAILS=true.
    """
    from datetime import datetime, timezone

    health_status: dict = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
    }

    if allow_public_error_details():
        import sys

        health_status["python_version"] = sys.version

    try:
        from .database import engine
        from sqlalchemy import text

        health_status["checks"]["database_backend"] = engine.dialect.name
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = (
            f"error: {str(e)}" if allow_public_error_details() else "error"
        )
        if "database_backend" not in health_status["checks"]:
            health_status["checks"]["database_backend"] = "unknown"
        health_status["status"] = "degraded"

    if allow_public_error_details():
        azure_openai_configured = bool(
            os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        health_status["checks"]["azure_openai"] = "ok" if azure_openai_configured else "not_configured"

        azure_search_configured = bool(
            os.getenv("AZURE_SEARCH_ENDPOINT") and os.getenv("AZURE_SEARCH_KEY")
        )
        health_status["checks"]["azure_search"] = "ok" if azure_search_configured else "not_configured"

    return health_status

@app.get("/api/status")
def api_status():
    """Minimal public probe unless ALLOW_PUBLIC_ERROR_DETAILS=true."""
    if allow_public_error_details():
        return {
            "api": "Jewish Coaching API",
            "version": "2.0.0",
            "bsd_version": "v2 (Single-Agent Conversational Coach)",
            "features": {
                "chat_v1": "available",
                "chat_v2": "available (default)",
                "speech": "available",
                "rag": "available",
                "calendar": "available",
            },
            "endpoints": {
                "health": "/health",
                "chat_v2": "/api/chat/v2/message",
                "speech_token": "/api/speech/token",
            },
        }
    return {"status": "ok"}

