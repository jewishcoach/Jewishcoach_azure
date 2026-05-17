#!/usr/bin/env bash
# Start the API locally with demo auth for localhost, bootstrap SQLite schema, run parallel load tests.
#
# Usage:
#   ./scripts/run_local_load_test.sh
#   WORKERS=10 LOAD_TEST_WARMUP=1 TIMEOUT=300 ./scripts/run_local_load_test.sh
#
# Requires: Python 3.11+ with venv support. Creates backend/.venv_loadtest on first run.
#
# Database: uses SQLite file backend/coaching_loadtest.db by default (ignores inherited DATABASE_URL).
#   LOAD_TEST_DATABASE_URL=... — alternate SQLite path or DB URL for the isolated run.
#   LOAD_TEST_USE_EXISTING_DB=1 — use current DATABASE_URL (e.g. Postgres); raise DB_POOL_SIZE if needed.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
cd "$BACKEND"

pick_python() {
  if [[ -n "${JC_PYTHON:-}" ]]; then
    echo "$JC_PYTHON"
    return
  fi
  if [[ -x "$BACKEND/.venv_loadtest/bin/python" ]]; then
    echo "$BACKEND/.venv_loadtest/bin/python"
    return
  fi
  if [[ -x "$BACKEND/jc_backend_venv/bin/python" ]]; then
    echo "$BACKEND/jc_backend_venv/bin/python"
    return
  fi
  echo "python3"
}

PY="$(pick_python)"

ensure_deps() {
  if "$PY" -c "from app.main import app" 2>/dev/null; then
    return 0
  fi
  echo "Bootstrapping $BACKEND/.venv_loadtest (first run can take a minute)..."
  python3 -m venv "$BACKEND/.venv_loadtest"
  PY="$BACKEND/.venv_loadtest/bin/python"
  "$PY" -m pip install -U pip wheel
  "$PY" -m pip install -r "$BACKEND/requirements-loadtest.txt"
}

ensure_deps

export ALLOW_DEMO_MODE="${ALLOW_DEMO_MODE:-true}"
export ALLOW_DEMO_LOCALHOST="${ALLOW_DEMO_LOCALHOST:-true}"
# Do not inherit DATABASE_URL from the shell by default — a shared Postgres pool (e.g. 5+10)
# will exhaust under 30 parallel requests. Use isolated SQLite unless opted in.
if [[ "${LOAD_TEST_USE_EXISTING_DB:-}" == "1" ]]; then
  : "${DATABASE_URL:?Set DATABASE_URL when LOAD_TEST_USE_EXISTING_DB=1}"
else
  export DATABASE_URL="${LOAD_TEST_DATABASE_URL:-sqlite:///./coaching_loadtest.db}"
fi
# SQLite default QueuePool is tiny; parallel load tests need more checkout slots.
export SQLITE_POOL_SIZE="${SQLITE_POOL_SIZE:-64}"
export SQLITE_MAX_OVERFLOW="${SQLITE_MAX_OVERFLOW:-64}"
export SQLITE_BUSY_TIMEOUT_SEC="${SQLITE_BUSY_TIMEOUT_SEC:-60}"

"$PY" -c "from app.database import engine, Base; import app.models; Base.metadata.create_all(bind=engine, checkfirst=True)"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-30}"
TIMEOUT="${TIMEOUT:-240}"

cleanup() {
  if [[ -n "${SRV_PID:-}" ]] && kill -0 "$SRV_PID" 2>/dev/null; then
    kill "$SRV_PID" 2>/dev/null || true
    wait "$SRV_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "Starting uvicorn on http://${HOST}:${PORT} ..."
"$PY" -m uvicorn app.main:app --host "$HOST" --port "$PORT" &
SRV_PID=$!

ready=0
for _ in $(seq 1 90); do
  if "$PY" -c "import urllib.request; urllib.request.urlopen('http://${HOST}:${PORT}/health', timeout=2)" 2>/dev/null; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" != "1" ]]; then
  echo "Server did not become healthy in time."
  exit 1
fi

echo "--- smoke /health (${WORKERS} parallel) ---"
BASE_URL="http://${HOST}:${PORT}" "$PY" "$ROOT/scripts/smoke_parallel_health.py" --workers "$WORKERS" --per-worker 1

LOAD_EXTRA=()
if [[ "${LOAD_TEST_WARMUP:-}" == "1" ]]; then
  LOAD_EXTRA+=(--warmup)
fi

echo "--- Chat V2 parallel (${WORKERS} workers, demo-localhost) ---"
BASE_URL="http://${HOST}:${PORT}" "$PY" "$ROOT/scripts/load_test_chat_v2_parallel.py" \
  --demo-localhost \
  --workers "$WORKERS" \
  --timeout "$TIMEOUT" \
  "${LOAD_EXTRA[@]}"

echo "All load checks finished."
