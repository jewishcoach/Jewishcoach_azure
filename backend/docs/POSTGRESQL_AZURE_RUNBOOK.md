# PostgreSQL on Azure — Runbook (Jewish Coach API)

**להנחיות קצרות בעברית (לא מתכנתים):** `MULTIUSER_SETUP_HE.md` — סקריפט אוטומטי + 3 צעדים.

מסמך הפעלה מקצועי: מעבר מ־SQLite קובץ ל־**Azure Database for PostgreSQL Flexible Server**, חיבור ל־**App Service** (`jewishcoach-api`), אימות, והעברת נתונים.

---

## 1. למה Postgres?

- SQLite מתאים לפיתוח / עומס נמוך; בפרודקשן עם בקשות מקביליות מופיעות נעילות (`database is locked`).
- PostgreSQL תומך במקביליות אמיתית; ניתן להריץ **יותר מ־Gunicorn worker אחד** (ראו `gunicorn_conf.py`).

---

## 2. דרישות מוקדמות

- מנוי Azure עם הרשאות ליצור **PostgreSQL Flexible Server** ו־**Firewall rules**.
- גיבוי מלא של `coaching.db` (או צילום לוגי לפני שינוי) לפני העברת נתונים.
- בריפו כבר קיים: `psycopg2-binary`, מנוע SQLAlchemy עם pool ל־Postgres, סקריפט `backend/scripts/sqlite_to_postgres.py`.

---

## 3. יצירת שרת Postgres ב-Azure (תקציר)

1. Portal → **Create** → **Azure Database for PostgreSQL** → **Flexible server**.
2. גרסה מומלפת: **15+**. אזור קרוב ל־App Service.
3. משתמש מנהל וסיסמה חזקים — שמרו את הסיסמה בצורה מאובטחת (Key Vault / secret manager).
4. **Networking**: התחילו ב־“Public access” עם חוק Firewall לכתובות היציאה של App Service, או השתמשו ב־**Private Endpoint** כשרשת סגורה נדרשת.
5. צרו מסד לוגי (למשל `jewishcoach`) או השתמשו בברירת המחדל `postgres` (פחות נקי לפרודקשן).

---

## 4. מחרוזת חיבור (`DATABASE_URL`)

פורמט מומלץ ליישום (SQLAlchemy + psycopg2):

```text
postgresql+psycopg2://ADMIN_USER:PASSWORD@FULL_HOST.postgres.database.azure.com:5432/DATABASE?sslmode=require
```

שימו לב:

- Azure לעיתים מציגה משתמש בצורה `user@hostname` — ייתכן שתידרש **קידוד URL** לחלק מהתווים בשם המשתמש או בסיסמה.
- תמיד **`sslmode=require`** לחיבור ציבורי מאובטח.

משתני כיוון עומס אופציונליים (ראו `backend/.env.example`):

| משתנה | משמעות |
|--------|--------|
| `DB_POOL_SIZE` | גודל pool בסיסי |
| `DB_MAX_OVERFLOW` | חיבורים נוספים בשיא |
| `DB_POOL_TIMEOUT` | שניות המתנה לחיבור מהבריכה |
| `DB_POOL_RECYCLE_SEC` | מחזור חיבורים לפני ניתוק אוטומטי (מתאים ל-Azure idle timeout) |

---

## 5. הגדרות ב-App Service

**דרך מהירה (מומלץ למי עם הרשאות Azure CLI):** מהשורש של הריפו:

```bash
export AZURE_PG_ADMIN_PASSWORD='…סיסמה-חזקה…'
bash scripts/azure_enable_postgres_for_multiuser.sh
```

(פרטים וצעדים למתחילים: `MULTIUSER_SETUP_HE.md`.)

**דרך ידנית בפורטל:**

ב־**jewishcoach-api** → **Configuration** → **Application settings**:

1. הוסיפו/עדכנו **`DATABASE_URL`** לערך Postgres (כמו בסעיף 4).
2. שמרו — האפליקציה תופעל מחדש.
3. אופציונלי: הגדירו **`GUNICORN_WORKERS=2`** (או יותר לפי SKU) — רק כש־`DATABASE_URL` **אינו** SQLite.

---

## 6. סכמה ביעד

בפריסה רגילה, **`startup.sh`** מריץ `Base.metadata.create_all` ומיגרציות עמודות אידמפוטנטיות. לאחר שינוי ל־Postgres, ההפעלה הראשונה תייצר טבלאות לפי המודלים.

---

## 7. העברת נתונים מ-SQLite (פעם אחת)

**אזהרה:** הסקריפט מבצע `TRUNCATE … CASCADE` על כל טבלאות ה־ORM ביעד Postgres.

```bash
cd backend
export SOURCE_DATABASE_URL='sqlite:////נתיב/מוחלט/coaching.db'
export DATABASE_URL='postgresql+psycopg2://...'
PYTHONPATH=. python3 scripts/sqlite_to_postgres.py --dry-run    # בדיקה בלבד
export CONFIRM_SQLITE_TO_PG_COPY=YES
PYTHONPATH=. python3 scripts/sqlite_to_postgres.py -v           # ביצוע
```

מומלץ להריץ ממכונה מהימנה עם גישת רשת ל־Postgres (לא בהכרח מהמחשב הציבורי ללא VPN/firewall).

---

## 8. אימות לאחר פריסה

- `GET https://<api-host>/health` — שדה `checks.database` צריך להיות `ok`, ו־`checks.database_backend` צריך להיות `postgresql`.
- בדיקת כניסה לאפליקציה + יצירת שיחה + עדכון preferences.

---

## 9. גלגול לאחור (Rollback)

- החזירו ב־App Service את `DATABASE_URL` ל־SQLite (זמני בלבד אם עדיין קיים הקובץ).
- תכננו מראש סביבת staging לפני שינוי production.

---

## 10. תקלות נפוצות

| תסמין | כיוון בדיקה |
|--------|-------------|
| שגיאת SSL | וודאו `sslmode=require` וששרת Postgres מאפשר חיבור מהכתובת שלכם. |
| Timeout / סירוב חיבור | Firewall של Postgres, או יותר מדי חיבורים — הגדילו SKU או כווננו pool. |
| שגיאות הרשאה | משתמש שגוי או סיסמה לא מקודדת נכון ב־URL. |

---

## 11. קישורים פנימיים בריפו

- `scripts/azure_enable_postgres_for_multiuser.sh` — הקמת Postgres + חיבור ל־Web App + workers (יציבות ריבוי משתמשים).
- `backend/docs/MULTIUSER_SETUP_HE.md` — מדריך בעברית בלי תשתית.
- `backend/app/database.py` — יצירת מנוע ובריכה.
- `backend/gunicorn_conf.py` — מספר workers לפי סוג DB.
- `backend/scripts/sqlite_to_postgres.py` — העברת נתונים.
- `backend/.env.example` — דוגמאות משתני סביבה.
