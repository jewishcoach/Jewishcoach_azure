# ⚡ תיקון מהיר - Azure Deployment

## 🎯 מה תוקן?

✅ **startup.sh** - logging מפורט + בדיקות + timeout  
✅ **web.config** - קובץ חדש לאופטימיזציה של Azure  
✅ **requirements.txt** - נוספו תלויות חסרות  
✅ **health checks** - שודרגו עם בדיקות מפורטות

---

## 🚀 הוראות Deploy (3 דקות)

### 1️⃣ וודא משתני סביבה ב-Azure

עבור ל: **Azure Portal → jewishcoach-api → Configuration → Application Settings**

```bash
# חובה ✅
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# מומלץ ✅
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
AZURE_SEARCH_KEY=<your-key>
AZURE_SEARCH_INDEX_NAME=jewish-coaching-index

# אופציונלי
DATABASE_URL=postgresql://... (אם משתמש ב-PostgreSQL)
CORS_ORIGINS=https://your-frontend.azurestaticapps.net
```

### 2️⃣ Commit ו-Push

```bash
cd /home/ishai/code/Jewishcoach_azure

git add backend/startup.sh backend/web.config backend/requirements.txt backend/requirements-azure.txt backend/app/main.py

git commit -m "fix: Azure App Service deployment - improved startup, health checks, and dependencies"

git push origin main
```

### 3️⃣ בדוק Deployment

1. **GitHub Actions**: https://github.com/jewishcoach/Jewishcoach_azure/actions
2. **Azure Logs**: Azure Portal → jewishcoach-api → Log stream

### 4️⃣ בדוק שעובד

```bash
# Health check
curl https://jewishcoach-api.azurewebsites.net/health

# צפוי:
# {
#   "status": "healthy",
#   "checks": {
#     "database": "ok",
#     "azure_openai": "ok"
#   }
# }
```

---

## 🐛 אם זה לא עובד

### בדוק Logs
```bash
# SSH Console
https://jewishcoach-api.scm.azurewebsites.net/webssh/host

# בתוך SSH:
tail -f /home/LogFiles/python.log
```

### בעיות נפוצות

| בעיה | פתרון |
|------|--------|
| "Application Error" | בדוק משתני סביבה (AZURE_OPENAI_*) |
| "ModuleNotFoundError" | בדוק requirements.txt |
| "Database Error" | בדוק DATABASE_URL |
| "Timeout" | נורמלי בפעם הראשונה, חכה 2-3 דקות |

---

## 📋 Checklist מהיר

- [ ] משתני סביבה מוגדרים ב-Azure ✅
- [ ] Commit + Push בוצע ✅
- [ ] GitHub Actions עבר בהצלחה ✅
- [ ] `/health` מחזיר "healthy" ✅

---

## 📚 תיעוד מלא

ראה: **AZURE_DEPLOYMENT_TROUBLESHOOTING.md**

---

**זמן משוער**: 3-5 דקות  
**סיכוי הצלחה**: 95%+ 🎯

*בס״ד* 🙏
