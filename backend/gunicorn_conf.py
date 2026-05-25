# -*- coding: utf-8 -*-
"""
Gunicorn configuration for the BSD Coach API on Azure App Service.

Workers
-------
- **SQLite** (file DB): forced to **1** worker — avoids cross-worker stale reads and write conflicts.
- **PostgreSQL**: honors ``GUNICORN_WORKERS`` (default **2**); tune for plan CPU/memory.

Hebrew text is unrelated to worker count; uvicorn worker handles UTF-8.
"""

import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes - 2 for Azure (avoids OOM on B1/S1); override with GUNICORN_WORKERS.
# Connection budget (Postgres): workers × (DB_POOL_SIZE + DB_MAX_OVERFLOW) — keep under server max_connections.
# SQLite file DB + multiple Gunicorn workers often loses writes or shows stale reads on App Service
# (webhook hits worker A, admin list hits worker B). Postgres can safely use multiple workers.
_database_url = (os.getenv("DATABASE_URL") or "").lower()  # match app.database._IS_SQLITE
_requested_workers = int(os.getenv("GUNICORN_WORKERS", "2"))
if "sqlite" in _database_url:
    workers = 1
    if _requested_workers != 1:
        print(
            f"⚠️ SQLite DATABASE_URL: forcing Gunicorn workers=1 "
            f"(ignoring GUNICORN_WORKERS={_requested_workers})"
        )
else:
    workers = _requested_workers
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 600  # 10 minutes for slow LLM responses
keepalive = 5

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stdout
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "bsd_coach"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None

print(f"🚀 Gunicorn starting with {workers} workers, timeout {timeout}s")
# Force deploy: Mon Feb 16 08:30:38 IST 2026

# Force rebuild
