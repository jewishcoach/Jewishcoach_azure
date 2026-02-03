#!/bin/bash
# Azure App Service startup script

echo "🚀 Starting Jewish Coach Backend..."

# Install dependencies
echo "📦 Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Create database if needed
echo "🗄️ Initializing database..."
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)" 2>/dev/null || true

# Start the application
echo "✅ Starting FastAPI with Uvicorn..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
