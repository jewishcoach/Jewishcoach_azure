# ריבוי משתמשים – הגדרת Scale

כשמשתמשים מרובים משתמשים באפליקציה במקביל, תגובות יכולות להאט (45–60 שניות). זה קורה בגלל:

1. **Azure App Service** – instance יחיד, workers מוגבלים
2. **Azure OpenAI** – מגבלות RPM/TPM (בקשות/טוקנים לדקה)
3. **תור בקשות** – בקשות מחכות ל-worker פנוי

## פתרונות מומלצים

### 1. Azure App Service – Scale Out

**ב-Azure Portal:** App Service → Scale out (App Service plan)

- **Manual:** 2–3 instances – כל instance מטפל בבקשות בנפרד
- **Autoscale:** הגדר rules לפי CPU או HTTP requests

```
לדוגמה: אם CPU > 70% → הוסף instance
```

### 2. Azure OpenAI – העלאת Tier

**ב-Azure Portal:** Azure OpenAI → Deployments → ה-deployment שלך

- **Standard S0:** ~240 RPM (בקשות לדקה)
- **Standard S1:** ~1,000 RPM – מתאים לריבוי משתמשים

אם יש throttling (429), העלה tier או צור deployment נוסף.

### 3. משתני סביבה (כבר מוגדרים בקוד)

| משתנה | ברירת מחדל | תיאור |
|-------|------------|-------|
| `GUNICORN_WORKERS` | 4 | מספר workers – העלה ל-6 אם יש 2+ vCPUs |
| `AZURE_OPENAI_TIMEOUT_SECONDS` | 90 | timeout ל-LLM – Azure יכול לקחת 45–60s |
| `AZURE_OPENAI_MAX_RETRIES` | 2 | retries על 429 throttling |

**ב-Azure:** App Service → Configuration → Application settings

### 4. Warmup (כבר מופעל)

ה-frontend קורא ל-`/api/chat/v2/warmup` בפתיחת שיחה – מחמם את prompt cache ב-Azure ומקצר תגובה ראשונה.

## בדיקת ביצועים

1. **משתמש יחיד** – אם מהיר (~3s) אבל 2 משתמשים איטי (~50s) → בעיית scale
2. **Azure Portal → Metrics** – בדוק latency, throttling, 429 errors
3. **לוגים** – `[PERF API] TOTAL API TIME` מראה כמה זמן לקח כל תגובה

## סיכום

| פעולה | איפה | השפעה |
|-------|------|--------|
| Scale out ל-2–3 instances | Azure Portal | כל instance מטפל במשתמשים בנפרד |
| העלאת Azure OpenAI tier | Azure Portal | יותר RPM, פחות throttling |
| GUNICORN_WORKERS=6 | App settings | יותר בקשות מקבילות באותו instance |
| Timeout 90s + Retries 2 | כבר בקוד | תגובות איטיות לא נכשלות |
