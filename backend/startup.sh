#!/bin/bash
set -e

echo "🚀 Starting Jewish Coach Backend..."
cd /home/site/wwwroot

# Persistent dependency cache in /home (survives restarts)
DEPS_DIR="/home/site/python_deps"
STATE_DIR="/home/site/startup_state"
REQ_FILE="/home/site/wwwroot/requirements.txt"
REQ_HASH_FILE="$STATE_DIR/requirements.sha256"

mkdir -p "$DEPS_DIR" "$STATE_DIR"

if [ ! -f "$REQ_FILE" ]; then
  echo "❌ requirements.txt not found at $REQ_FILE"
  exit 1
fi

CURRENT_HASH=$(sha256sum "$REQ_FILE" | awk '{print $1}')
PREV_HASH=""
if [ -f "$REQ_HASH_FILE" ]; then
  PREV_HASH=$(cat "$REQ_HASH_FILE")
fi

# Install deps only on first boot or when requirements changed
if [ "$CURRENT_HASH" != "$PREV_HASH" ]; then
  echo "📦 requirements changed (or first boot) -> installing dependencies..."
  python -m pip install --upgrade pip --no-cache-dir
  python -m pip install -r "$REQ_FILE" --target "$DEPS_DIR" --no-cache-dir --ignore-installed
  echo "$CURRENT_HASH" > "$REQ_HASH_FILE"
  echo "✅ Dependencies installed in $DEPS_DIR"
else
  echo "✅ Dependency cache hit, skipping pip install"
fi

export PYTHONPATH="$DEPS_DIR:/home/site/wwwroot:${PYTHONPATH}"
export PYTHONUTF8=1
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
PORT="${PORT:-8000}"

echo "🌐 Port: $PORT"
echo "📚 PYTHONPATH: $PYTHONPATH"

# Optional DB init (single process, checkfirst avoids duplicate table create)
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine, checkfirst=True)" 2>&1 || true

echo "🚀 Launching Gunicorn..."
if [ -f "/home/site/wwwroot/gunicorn_conf.py" ]; then
  exec gunicorn -c /home/site/wwwroot/gunicorn_conf.py app.main:app
else
  echo "⚠️ gunicorn_conf.py missing, starting with safe inline defaults"
  exec gunicorn \
    -w "${GUNICORN_WORKERS:-2}" \
    -k uvicorn.workers.UvicornWorker \
    app.main:app \
    --bind "0.0.0.0:${PORT}" \
    --timeout "${GUNICORN_TIMEOUT:-600}" \
    --access-logfile - \
    --error-logfile - \
    --log-level info
fi
