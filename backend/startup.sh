#!/bin/bash
# Azure App Service startup script

cd /home/site/wwwroot || exit 1

# Install dependencies
python -m pip install --upgrade pip --no-cache-dir
python -m pip install -r requirements.txt --no-cache-dir

# Set PYTHONPATH
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Create database
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)" 2>/dev/null || true

# Start application
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
