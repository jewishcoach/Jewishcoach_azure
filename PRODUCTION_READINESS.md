# מוכנות לפרודקשן וריבוי משתמשים

סקירה של מה קיים ומה חסר לפני הרצה בפרודקשן עם משתמשים מרובים.

## ✅ מה קיים

### אבטחה
- **אימות (Clerk JWT)** – `get_current_user` ב-dependencies, סינכרון משתמש ל-DB
- **אימות בעלות** – Chat V2: `_get_conversation_or_404` ב-send_message, debug, insights
- **CORS** – מוגדר ב-main.py (CORS_ORIGINS, ALLOW_TUNNELS, azurestaticapps.net)
- **Secrets** – משתני סביבה (DATABASE_URL, Azure keys) – לא בקוד

### שימוש ומגבלות
- **Usage limits** – `check_usage_limit`, `increment_usage` ב-billing
- **Usage limiter middleware** – `backend/app/middleware/usage_limiter.py` (check_message_limit, check_speech_limit)
- **הערה:** ה-middleware לא מחובר כרגע ל-chat endpoints – יש לחבר אם רוצים לאכוף מכסות

### Scale ו-Performance
- **MULTI_USER_SCALING.md** – הנחיות Scale Out, Azure OpenAI tier, GUNICORN_WORKERS
- **Warmup** – `/api/chat/v2/warmup` מחמם prompt cache
- **Rate limit fallback** – טיפול ב-429 ב-single_agent_coach (הודעת "עומס רגעי")
- **Timeout & retries** – AZURE_OPENAI_TIMEOUT_SECONDS, AZURE_OPENAI_MAX_RETRIES

### לוגים
- **Gunicorn** – accesslog, errorlog ל-stdout (Azure לוגים)
- **BSD/API** – `logger.info` עם `[PERF API]`, `[BSD V2]` וכו'
- **Error buffer** – `capture_error` + `get_recent_errors` לדיבוג

### CI/CD
- **CI** – lint, build, prompt tests, pytest (ownership)
- **Deploy** – prompt tests, pytest, zip, Azure Web Apps Deploy

---

## ⚠️ מה חסר או מומלץ לשפר

### 1. אימות JWT
- **נוכחי:** `jwt.get_unverified_claims(token)` – לא מאמת חתימה
- **מומלץ:** אימות JWT עם Clerk JWKS (או `clerk-sdk`) לפני פרודקשן

### 2. Rate limiting (בקשות לדקה)
- **נוכחי:** אין rate limiting לפי IP או משתמש
- **מומלץ:** slowapi או middleware דומה להגנה מ-DoS / abuse

### 3. חיבור Usage Limiter
- **נוכחי:** `check_message_limit` קיים אך לא נקרא מ-send_message
- **מומלץ:** להוסיף dependency/check לפני שליחת הודעה

### 4. Monitoring & Alerts
- **נוכחי:** לוגים ל-stdout, אין Application Insights / metrics
- **מומלץ:** Application Insights, התראות על 5xx, latency גבוה

### 5. Database
- **נוכחי:** SQLAlchemy sync, connection per request
- **מומלץ:** connection pooling (כבר ברירת מחדל), בדיקת health תקופתית

### 6. .gitignore
- **נוכחי:** `antenv/` ו-`test_venv/` לא ב-.gitignore
- **מומלץ:** להוסיף כדי למנוע commit של venv

---

## סיכום עדיפויות

| עדיפות | פעולה | השפעה |
|--------|-------|-------|
| גבוהה | אימות JWT מלא (Clerk JWKS) | אבטחה |
| גבוהה | חיבור usage_limiter ל-chat | מניעת שימוש חורג |
| בינונית | Rate limiting (slowapi) | הגנה מ-abuse |
| בינונית | Application Insights | ניטור ותגובה מהירה |
| נמוכה | .gitignore ל-antenv | ניקיון repo |
