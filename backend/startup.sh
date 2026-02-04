#!/bin/bash
cd /home/site/wwwroot
python -m pip install --upgrade pip --no-cache-dir
python -m pip install -r requirements.txt --no-cache-dir
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)" 2>/dev/null || true
exec gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
