"""Debug endpoint to fetch recent logs"""
from fastapi import APIRouter
import subprocess
import os

router = APIRouter()

@router.get("/debug/logs")
async def get_recent_logs():
    """Get recent application logs"""
    try:
        # Try to read Gunicorn logs
        log_locations = [
            "/home/LogFiles/application.log",
            "/home/LogFiles/stdout*.log",
            "/var/log/app.log",
            "logs/gunicorn.log"
        ]
        
        logs = []
        for log_path in log_locations:
            if '*' in log_path:
                # Use glob pattern
                import glob
                files = glob.glob(log_path)
                for f in files:
                    if os.path.exists(f):
                        try:
                            with open(f, 'r') as lf:
                                content = lf.readlines()
                                logs.append({
                                    "file": f,
                                    "lines": content[-100:]  # Last 100 lines
                                })
                        except:
                            pass
            else:
                if os.path.exists(log_path):
                    try:
                        with open(log_path, 'r') as lf:
                            content = lf.readlines()
                            logs.append({
                                "file": log_path,
                                "lines": content[-100:]  # Last 100 lines
                            })
                    except:
                        pass
        
        # Also try to get stdout/stderr from system
        try:
            result = subprocess.run(
                ['tail', '-n', '200', '/tmp/gunicorn.log'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.stdout:
                logs.append({
                    "file": "/tmp/gunicorn.log",
                    "lines": result.stdout.split('\n')
                })
        except:
            pass
        
        return {
            "status": "ok",
            "found_logs": len(logs),
            "logs": logs,
            "checked_locations": log_locations
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
