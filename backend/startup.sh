#!/bin/bash
set -e  # Exit on error

echo "🚀 Starting Jewish Coach Backend..."
echo "📁 Working directory: $(pwd)"

# Navigate to app directory
cd /home/site/wwwroot
echo "✅ Changed to /home/site/wwwroot"

# Upgrade pip
echo "📦 Upgrading pip..."
python -m pip install --upgrade pip --no-cache-dir
echo "✅ Pip upgraded"

# Install dependencies
echo "📦 Installing dependencies from requirements.txt..."
python -m pip install -r requirements.txt --no-cache-dir
echo "✅ Dependencies installed"

# Set Python path
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH
echo "✅ PYTHONPATH set to: $PYTHONPATH"

# Check critical environment variables
echo "🔍 Checking environment variables..."
if [ -z "$AZURE_OPENAI_API_KEY" ]; then
    echo "⚠️  WARNING: AZURE_OPENAI_API_KEY not set"
else
    echo "✅ AZURE_OPENAI_API_KEY is set"
fi

if [ -z "$AZURE_OPENAI_ENDPOINT" ]; then
    echo "⚠️  WARNING: AZURE_OPENAI_ENDPOINT not set"
else
    echo "✅ AZURE_OPENAI_ENDPOINT is set"
fi

# Initialize database
echo "🗄️  Initializing database..."
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)" 2>&1 || echo "⚠️  Database initialization failed (may be normal)"
echo "✅ Database initialization complete"

# Get port from Azure (default 8000)
PORT="${PORT:-8000}"
echo "🌐 Using port: $PORT"

# Start gunicorn with uvicorn workers
echo "🚀 Starting Gunicorn with Uvicorn workers..."
echo "   Workers: 2"
echo "   Bind: 0.0.0.0:$PORT"
echo "   Timeout: 120s"

exec gunicorn \
    -w 2 \
    -k uvicorn.workers.UvicornWorker \
    app.main:app \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
