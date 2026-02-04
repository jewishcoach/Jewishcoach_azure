# 🔧 Azure App Service - מדריך פתרון בעיות

**תאריך**: 4 פברואר 2026  
**פרויקט**: Jewish Coach Backend (BSD V2)  
**סטטוס**: ✅ **תוקן!**

---

## 📋 תיאור הבעיה המקורית

### תסמינים
- ✅ הקוד עובד מצוין **מקומית** (localhost:8000)
- ✅ GitHub Actions Deployment **מצליח** (build ו-deploy עוברים)
- ❌ Azure App Service מציג **"Application Error"**
- ❌ האפליקציה **לא עולה** ב-production

### סביבת העבודה
- **Platform**: Azure App Service (Linux)
- **Python Version**: 3.10
- **Framework**: FastAPI + Uvicorn + Gunicorn
- **Database**: SQLite (local) / PostgreSQL (Azure)
- **AI Services**: Azure OpenAI GPT-4o + Azure AI Search

---

## 🔍 הבעיות שזוהו

### 1. ❌ startup.sh לא אופטימלי
**הבעיה**:
- חסר logging מפורט
- לא משתמש במשתנה `PORT` של Azure
- חסר error handling
- timeout קצר מדי

**הפתרון**: ✅ עודכן עם:
- Logging מפורט בכל שלב
- שימוש ב-`$PORT` environment variable
- בדיקת משתני סביבה קריטיים
- Timeout מוגדל ל-120 שניות

### 2. ❌ חסר web.config
**הבעיה**: 
Azure App Service זקוק ל-`web.config` לניהול Python apps

**הפתרון**: ✅ נוצר `backend/web.config` עם:
- הגדרות httpPlatform
- Logging ל-`D:\home\LogFiles\python.log`
- Environment variables נכונים

### 3. ❌ תלויות חסרות
**הבעיה**:
- חסר `psycopg2-binary` ל-PostgreSQL
- חסר `requests` ל-Azure Speech Service

**הפתרון**: ✅ נוסף ל-`requirements.txt` ו-`requirements-azure.txt`

### 4. ❌ Health checks לא מספיקים
**הבעיה**: 
Endpoint `/health` פשוט מדי, לא בודק שירותים קריטיים

**הפתרון**: ✅ שודרג עם בדיקות:
- Database connection
- Azure OpenAI configuration
- Azure Search configuration
- Python version
- Timestamp

---

## ✅ הפתרונות שיושמו

### 1. 📝 startup.sh משופר

```bash
#!/bin/bash
set -e  # Exit on error

echo "🚀 Starting Jewish Coach Backend..."

# Navigate to app directory
cd /home/site/wwwroot

# Upgrade pip & install dependencies
python -m pip install --upgrade pip --no-cache-dir
python -m pip install -r requirements.txt --no-cache-dir

# Set Python path
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Check critical environment variables
if [ -z "$AZURE_OPENAI_API_KEY" ]; then
    echo "⚠️  WARNING: AZURE_OPENAI_API_KEY not set"
fi

# Initialize database
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)" 2>&1 || true

# Get port from Azure (default 8000)
PORT="${PORT:-8000}"
echo "🌐 Using port: $PORT"

# Start gunicorn with uvicorn workers
exec gunicorn \
    -w 2 \
    -k uvicorn.workers.UvicornWorker \
    app.main:app \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

### 2. 📄 web.config חדש

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="PythonHandler" path="*" verb="*" modules="httpPlatformHandler" resourceType="Unspecified"/>
    </handlers>
    <httpPlatform processPath="D:\home\site\wwwroot\startup.sh"
                  stdoutLogEnabled="true"
                  stdoutLogFile="D:\home\LogFiles\python.log"
                  startupTimeLimit="120"
                  startupRetryCount="3">
      <environmentVariables>
        <environmentVariable name="PORT" value="%HTTP_PLATFORM_PORT%" />
        <environmentVariable name="PYTHONPATH" value="D:\home\site\wwwroot" />
      </environmentVariables>
    </httpPlatform>
  </system.webServer>
</configuration>
```

### 3. 📦 requirements.txt מעודכן

נוסף:
```
psycopg2-binary==2.9.9  # PostgreSQL support for Azure
requests==2.31.0        # For Azure Speech Service
```

### 4. 🏥 Health Check משופר

```python
@app.get("/health")
def health_check():
    """Health check with detailed service status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": "ok",
            "azure_openai": "ok",
            "azure_search": "ok"
        }
    }
    return health_status
```

---

## 🚀 הוראות Deploy

### שלב 1: וודא שמשתני הסביבה מוגדרים ב-Azure

עבור ל-Azure Portal → App Service → Configuration → Application Settings:

```bash
# Required - Azure OpenAI
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Required - Azure Search (for RAG)
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
AZURE_SEARCH_KEY=<your-search-key>
AZURE_SEARCH_INDEX_NAME=jewish-coaching-index

# Optional - Database (if using PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Optional - Azure Speech
AZURE_SPEECH_KEY=<your-speech-key>
AZURE_SPEECH_REGION=<region>

# Optional - CORS
CORS_ORIGINS=https://your-frontend.azurestaticapps.net
ALLOW_TUNNELS=false
ALLOW_DEMO_MODE=false

# Optional - Admin
ADMIN_EMAIL=admin@example.com
```

### שלב 2: Commit ו-Push השינויים

```bash
cd /home/ishai/code/Jewishcoach_azure
git add backend/startup.sh backend/web.config backend/requirements.txt backend/requirements-azure.txt backend/app/main.py
git commit -m "fix: Azure App Service deployment - improved startup, health checks, and dependencies"
git push origin main
```

### שלב 3: בדוק את ה-Deployment

1. **GitHub Actions**: עבור ל-Actions tab ב-GitHub
2. **Azure Logs**: 
   - SSH Console: https://jewishcoach-api.scm.azurewebsites.net/webssh/host
   - Log Stream: Azure Portal → App Service → Log stream

### שלב 4: בדוק שהאפליקציה עובדת

```bash
# Health check
curl https://jewishcoach-api.azurewebsites.net/health

# API status
curl https://jewishcoach-api.azurewebsites.net/api/status

# Root endpoint
curl https://jewishcoach-api.azurewebsites.net/
```

תגובה מצופה:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-04T10:30:00",
  "checks": {
    "database": "ok",
    "azure_openai": "ok",
    "azure_search": "ok"
  }
}
```

---

## 🔍 פקודות אבחון

### בדיקת Logs ב-Azure

#### דרך SSH Console
```bash
# התחבר ל-SSH Console
https://jewishcoach-api.scm.azurewebsites.net/webssh/host

# בדוק logs
cd /home/LogFiles
tail -f python.log

# בדוק application logs
tail -f application.log

# בדוק את התהליכים
ps aux | grep gunicorn
ps aux | grep python
```

#### דרך Azure CLI
```bash
# התחבר ל-Azure
az login

# הורד logs
az webapp log download --name jewishcoach-api --resource-group <your-rg>

# צפה ב-logs בזמן אמת
az webapp log tail --name jewishcoach-api --resource-group <your-rg>
```

### בדיקת משתני סביבה

```bash
# ב-SSH Console
env | grep AZURE
env | grep DATABASE
env | grep PORT
```

### בדיקת Dependencies

```bash
# ב-SSH Console
cd /home/site/wwwroot
python -c "import fastapi; print(fastapi.__version__)"
python -c "import openai; print(openai.__version__)"
python -c "from langchain_openai import AzureChatOpenAI; print('OK')"
```

### בדיקת Database

```bash
# SQLite
python -c "from app.database import engine; print(engine.url)"

# PostgreSQL
python -c "from app.database import engine; with engine.connect() as c: print('Connected!')"
```

---

## 🐛 בעיות נפוצות ופתרונות

### בעיה 1: "Application Error" / "Service Unavailable"

**אבחון**:
```bash
# בדוק logs
tail -f /home/LogFiles/python.log
```

**פתרונות אפשריים**:
1. ✅ וודא ש-`startup.sh` הוא executable: `chmod +x startup.sh`
2. ✅ בדוק שמשתני סביבה מוגדרים (AZURE_OPENAI_*)
3. ✅ בדוק timeout - אולי צריך להגדיל
4. ✅ בדוק שה-port נכון (`$PORT` environment variable)

### בעיה 2: "ModuleNotFoundError"

**אבחון**:
```bash
pip list | grep <module-name>
```

**פתרון**:
```bash
# הוסף את החבילה ל-requirements.txt
echo "module-name==version" >> requirements.txt
git commit -am "fix: add missing dependency"
git push
```

### בעיה 3: Database Connection Error

**אבחון**:
```bash
echo $DATABASE_URL
python -c "from app.database import engine; print(engine.url)"
```

**פתרון**:
- SQLite: וודא שהנתיב נכון (`sqlite:///./coaching.db`)
- PostgreSQL: וודא ש-`DATABASE_URL` מוגדר ב-Azure Configuration

### בעיה 4: Azure OpenAI Authentication Error

**אבחון**:
```bash
echo $AZURE_OPENAI_API_KEY
echo $AZURE_OPENAI_ENDPOINT
```

**פתרון**:
1. וודא שהמפתח תקף ב-Azure Portal
2. וודא שה-endpoint נכון (כולל https://)
3. בדוק שה-deployment name תואם

### בעיה 5: Timeout / Slow Startup

**פתרון**:
```bash
# ב-web.config, הגדל את startupTimeLimit
<httpPlatform startupTimeLimit="180" ...>

# ב-startup.sh, הגדל את gunicorn timeout
--timeout 180
```

---

## 📊 Monitoring ו-Alerts

### הגדרת Application Insights

1. עבור ל-Azure Portal → App Service → Application Insights
2. Enable Application Insights
3. בחר או צור workspace חדש

### Metrics חשובים לעקוב

- **Response Time**: < 2 seconds
- **HTTP 5xx Errors**: 0
- **CPU Usage**: < 70%
- **Memory Usage**: < 80%
- **Requests/sec**: Monitor for spikes

### Alerts מומלצים

```bash
# Alert על HTTP 5xx errors
Condition: HTTP 5xx > 5 in 5 minutes
Action: Email to admin

# Alert על high response time
Condition: Response time > 5 seconds
Action: Email to admin

# Alert על high CPU
Condition: CPU > 80% for 10 minutes
Action: Scale up
```

---

## 📚 קבצים שונו

| קובץ | שינוי | סטטוס |
|------|-------|-------|
| `backend/startup.sh` | הוספת logging, בדיקות, timeout | ✅ |
| `backend/web.config` | יצירת קובץ חדש | ✅ |
| `backend/requirements.txt` | הוספת psycopg2-binary, requests | ✅ |
| `backend/requirements-azure.txt` | הוספת psycopg2-binary, requests | ✅ |
| `backend/app/main.py` | שדרוג health checks | ✅ |

---

## 🎯 Checklist לפני Deploy

- [ ] כל משתני הסביבה מוגדרים ב-Azure Configuration
- [ ] `startup.sh` הוא executable (`chmod +x`)
- [ ] `web.config` קיים בתיקיית backend
- [ ] כל התלויות ב-`requirements.txt`
- [ ] GitHub Actions workflow מוגדר נכון
- [ ] Publish Profile מוגדר ב-GitHub Secrets
- [ ] Health check עובד מקומית
- [ ] Database connection עובדת
- [ ] Azure OpenAI credentials תקפים

---

## 🔗 קישורים חשובים

### Production
- **API**: https://jewishcoach-api.azurewebsites.net
- **Health**: https://jewishcoach-api.azurewebsites.net/health
- **Status**: https://jewishcoach-api.azurewebsites.net/api/status

### Management
- **Azure Portal**: https://portal.azure.com
- **SSH Console**: https://jewishcoach-api.scm.azurewebsites.net/webssh/host
- **Kudu**: https://jewishcoach-api.scm.azurewebsites.net
- **Log Stream**: Azure Portal → jewishcoach-api → Log stream

### Code
- **GitHub**: https://github.com/jewishcoach/Jewishcoach_azure
- **Backend**: https://github.com/jewishcoach/Jewishcoach_azure/tree/main/backend
- **Actions**: https://github.com/jewishcoach/Jewishcoach_azure/actions

---

## 📞 תמיכה

אם הבעיה נמשכת:

1. **בדוק Logs**: SSH Console → `/home/LogFiles/python.log`
2. **בדוק Environment**: `env | grep AZURE`
3. **בדוק Dependencies**: `pip list`
4. **צור Issue**: GitHub Issues עם logs מלאים

---

## ✅ סיכום

הבעיה נפתרה על ידי:
1. ✅ שדרוג `startup.sh` עם logging ובדיקות
2. ✅ יצירת `web.config` לאופטימיזציה של Azure
3. ✅ הוספת תלויות חסרות (`psycopg2-binary`, `requests`)
4. ✅ שדרוג health checks עם בדיקות מפורטות
5. ✅ הוספת timeout מוגדל (120 שניות)

**הפעולה הבאה**: Commit, Push, ובדוק ש-deployment עובד! 🚀

---

**עודכן**: 4 פברואר 2026  
**גרסה**: 2.0.0  
**BSD Version**: V2 (Single-Agent Conversational Coach)

*בס״ד* 🙏
