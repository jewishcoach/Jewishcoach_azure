#!/bin/bash
# Azure App Service startup script

set -e  # Exit on error

echo "🚀 Starting Jewish Coach Backend..."
echo "📍 Current directory: $(pwd)"
echo "📂 Files: $(ls -la)"

# Install dependencies
echo "📦 Installing Python dependencies..."
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Set PYTHONPATH
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH
echo "✅ PYTHONPATH set to: $PYTHONPATH"

# Create database if needed
echo "🗄️ Initializing database..."
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)" 2>/dev/null || echo "Database init skipped or failed (will retry on first request)"

# Start the application
echo "✅ Starting FastAPI with Uvicorn on port 8000..."
exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind=0.0.0.0:8000 --timeout=120 --access-logfile=- --error-logfile=-
