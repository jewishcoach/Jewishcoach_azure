# יציבות ריבוי משתמשים — מדריך קצר (בלי תשתית)

מטרה: שהאפליקציה תפסיק להיסגר על **נעילות SQLite** כשהרבה אנשים נכנסים ביחד. הפתרון המקצועי הוא **PostgreSQL בענן**, מחובר ל־Web App שלך.

---

## השורה התחתונה

1. יש סקריפט אחד בריפו שיוצר את שרת Postgres ב־Azure (בתשלום חודשי), פותח גישה מהאפליקציה, ומעדכן את ההגדרות.
2. אחרי ההרצה האפליקציה עובדת עם מסד **חדש וריק** — משתמשים מזוהים דרך Clerk כרגיל, אבל **היסטוריית שיחות ישנה** לא עוברת לבד. אם צריך להעביר נתונים מהקובץ הישן, זה שלב נפרד (במסמך הטכני).

---

## מה אתה צריך לעשות (3 צעדים)

### 1) התקן והתחבר ל-Azure מהמחשב

- התקן **Azure CLI** (חיפוש: “Install Azure CLI”).
- בטרמינל הרץ:

```bash
az login --use-device-code
```

הסבר למסך ואשר בדפדפן.

### 2) בחר סיסמת מנהל למסד הנתונים

סיסמה חזקה, **לפחות 12 תווים**, שלא תישמר בגיט:

```bash
export AZURE_PG_ADMIN_PASSWORD='הסיסמה-שלך-כאן'
```

### 3) הרץ את הסקריפט מתיקיית הפרויקט

```bash
cd /path/to/Jewishcoach_azure
bash scripts/azure_enable_postgres_for_multiuser.sh
```

כשישאלו — הקלד `yes` ואשר.

הסקריפט מדפיס בסוף כתובת ל־`/health` — פתח אותה ובדוק ש־`database` הוא `ok` וש־`database_backend` הוא `postgresql`.

---

## עלויות ומה חשוב לדעת

- שרת PostgreSQL ב-Azure הוא **שירות בתשלום** (בדרך כלל סכום קבוע חודשי תלוי אזור וגודל; מתחילים ברמת קטן).
- אם השם `jewishcoach-pg` תפוס אצלך ב-Azure, הרץ עם שם אחר:

```bash
export AZURE_PG_SERVER_NAME=שם-ייחודי-שלך
bash scripts/azure_enable_postgres_for_multiuser.sh
```

---

## אוטומציה / CI

להרצה בלי שאלות:

```bash
export SKIP_CONFIRM=1
bash scripts/azure_enable_postgres_for_multiuser.sh
```

---

## פרטים טכניים והעברת נתונים ישנים

- מדריך מלא (נדרש למפתח): `backend/docs/POSTGRESQL_AZURE_RUNBOOK.md`
- העברה מ־SQLite (מכונה מהימנה + גיבוי): `backend/scripts/sqlite_to_postgres.py`
