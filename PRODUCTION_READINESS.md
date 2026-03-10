# מוכנות לפרודקשן וריבוי משתמשים

סקירה של מה קיים ומה חסר לפני הרצה בפרודקשן עם משתמשים מרובים.

## ✅ מה קיים

### אבטחה
- **אימות (Clerk JWT)** – `get_current_user` ב-dependencies. אם `CLERK_JWKS_URL` מוגדר – אימות חתימה עם JWKS; אחרת unverified (dev)
- **אימות בעלות** – Chat V2: `_get_conversation_or_404` ב-send_message, debug, insights
- **CORS** – מוגדר ב-main.py (CORS_ORIGINS, ALLOW_TUNNELS, azurestaticapps.net)
- **Secrets** – משתני סביבה (DATABASE_URL, Azure keys) – לא בקוד

### שימוש ומגבלות
- **Usage limits** – `check_usage_limit`, `increment_usage` ב-billing
- **Usage limiter** – מחובר ל-chat V1 ו-V2 (require_message_quota dependency)
- **Rate limiting** – slowapi 30/דקה ל-chat (לפי IP)

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

### 1. אימות JWT בפרודקשן
- **נוכחי:** אם `CLERK_JWKS_URL` לא מוגדר – unverified. להגדיר בפרודקשן.
- **דוגמה:** `CLERK_JWKS_URL=https://<instance>.clerk.accounts.dev/.well-known/jwks.json`

### 2. Rate limiting
- **נוכחי:** slowapi – 30 בקשות/דקה ל-chat endpoints (לפי IP)

### 3. Monitoring & Alerts
- **נוכחי:** לוגים ל-stdout, אין Application Insights / metrics
- **מומלץ:** Application Insights, התראות על 5xx, latency גבוה

### 4. Database
- **נוכחי:** SQLAlchemy sync, connection per request
- **מומלץ:** connection pooling (כבר ברירת מחדל), בדיקת health תקופתית

### 5. .gitignore
- **נוכחי:** נוספו `antenv/`, `test_venv/`, `.venv/`

---

## סיכום – מה בוצע

| פעולה | סטטוס |
|-------|-------|
| אימות JWT עם JWKS (CLERK_JWKS_URL) | ✅ |
| חיבור usage_limiter ל-chat | ✅ |
| Rate limiting (slowapi) | ✅ |
| .gitignore ל-antenv | ✅ |
| Application Insights | ⏳ מומלץ |
