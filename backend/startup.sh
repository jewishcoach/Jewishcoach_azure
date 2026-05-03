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

# DB init: create new tables if missing
python -c "from app.database import engine, Base; import app.models; Base.metadata.create_all(bind=engine, checkfirst=True)" 2>&1 || true

# Column migrations: add new columns to existing tables (idempotent)
# Uses app.database.engine directly so it targets the same DB the app uses.
python -c "
from app.database import engine
from sqlalchemy import text, inspect as sa_inspect
try:
    insp = sa_inspect(engine)
    cols = [c['name'] for c in insp.get_columns('conversations')]
    if 'updated_at' not in cols:
        with engine.connect() as conn:
            conn.execute(text('ALTER TABLE conversations ADD COLUMN updated_at TIMESTAMP'))
            conn.commit()
        print('✓ Added updated_at column to conversations')
    else:
        print('✓ updated_at column already present')
except Exception as e:
    print(f'⚠️  Column migration warning: {e}')
" 2>&1 || true

# Users: discipline columns (must match app.models.User — fixes prod SQLite missing columns)
python -c "
from app.database import engine
from sqlalchemy import text, inspect as sa_inspect
try:
    insp = sa_inspect(engine)
    with engine.connect() as conn:
        cols = [c['name'] for c in insp.get_columns('users')]
        if 'primary_discipline' not in cols:
            conn.execute(text('ALTER TABLE users ADD COLUMN primary_discipline VARCHAR'))
            conn.commit()
            print('✓ Added primary_discipline to users')
        else:
            print('✓ primary_discipline already present on users')
        cols = [c['name'] for c in insp.get_columns('users')]
        if 'mentor_disciplines' not in cols:
            conn.execute(text('ALTER TABLE users ADD COLUMN mentor_disciplines TEXT'))
            conn.commit()
            print('✓ Added mentor_disciplines to users')
        else:
            print('✓ mentor_disciplines already present on users')
except Exception as e:
    print(f'⚠️  users discipline column migration: {e}')
" 2>&1 || true

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
