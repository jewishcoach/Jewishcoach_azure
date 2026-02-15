from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import chat, speech, feedback, users, journal, tools, admin, billing, profile, calendar
from .api import chat_v2, debug_health, version  # BSD V2 + Debug + Version
import os
from dotenv import load_dotenv

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Jewish Coaching API",
    description="AI Coaching platform with RAG and Voice support",
    version="1.0.0"
)

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

# Check if we should allow remote tunneling domains (useful for external testing)
allow_tunnels = os.getenv("ALLOW_TUNNELS", "true").lower() == "true"

if allow_tunnels:
    # Add regex patterns to allow tunneling services: ngrok, localhost.run, etc.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list,
        allow_origin_regex=r"https://.*\.(ngrok-free\.app|lhr\.life|localhost\.run)",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print("✅ CORS: Remote tunneling enabled (ngrok, localhost.run, etc.)")
else:
    # Standard CORS for specific origins only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print(f"✅ CORS: Configured for origins: {origins_list}")

# Include routers
app.include_router(chat.router)  # V1 - Multi-layer architecture
app.include_router(chat_v2.router)  # V2 - Single-agent conversational coach
app.include_router(debug_health.router)  # Debug endpoints
app.include_router(version.router)  # Version check
app.include_router(speech.router)
app.include_router(feedback.router)
app.include_router(users.router)
app.include_router(journal.router)
app.include_router(tools.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(profile.router)
app.include_router(calendar.router)

@app.get("/")
def root():
    return {
        "message": "Jewish Coaching API",
        "status": "running",
        "version": "2.0.0",
        "bsd_version": "v2"
    }

@app.get("/health")
def health_check():
    """
    Health check endpoint for Azure App Service.
    Returns detailed status of all critical services.
    """
    import sys
    from datetime import datetime
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": sys.version,
        "checks": {}
    }
    
    # Check database connection
    try:
        from .database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Azure OpenAI configuration
    azure_openai_configured = bool(
        os.getenv("AZURE_OPENAI_API_KEY") and 
        os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    health_status["checks"]["azure_openai"] = "ok" if azure_openai_configured else "not_configured"
    
    # Check Azure Search configuration
    azure_search_configured = bool(
        os.getenv("AZURE_SEARCH_ENDPOINT") and 
        os.getenv("AZURE_SEARCH_KEY")
    )
    health_status["checks"]["azure_search"] = "ok" if azure_search_configured else "not_configured"
    
    return health_status

@app.get("/api/status")
def api_status():
    """
    Detailed API status endpoint.
    """
    return {
        "api": "Jewish Coaching API",
        "version": "2.0.0",
        "bsd_version": "v2 (Single-Agent Conversational Coach)",
        "features": {
            "chat_v1": "available",
            "chat_v2": "available (default)",
            "speech": "available",
            "rag": "available",
            "calendar": "available"
        },
        "endpoints": {
            "health": "/health",
            "chat_v2": "/api/chat/v2/message",
            "speech_token": "/api/speech/token"
        }
    }

