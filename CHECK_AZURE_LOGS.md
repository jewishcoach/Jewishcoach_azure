# בדיקת לוגים ב-Azure – מדריך

## ✅ איך לקרוא לוגים (Kudu API)

**`az webapp log download`** יוצר zip פגום ב-Linux – בעיה ידועה. השתמש ב-**Kudu VFS API**:

```bash
# 1. קבל credentials
CREDS=$(az webapp deployment list-publishing-profiles \
  --name jewishcoach-api --resource-group jewish-coach-rg \
  --query "[?publishMethod=='MSDeploy'].{user:userName,pass:userPWD}" -o json | \
  python3 -c "import sys, json; d=json.load(sys.stdin)[0]; print(f\"{d['user']}:{d['pass']}\")")

# 2. רשימת קבצי לוג
curl -s -u "$CREDS" "https://jewishcoach-api.scm.azurewebsites.net/api/vfs/LogFiles/"

# 3. קריאת לוג (החלף את שם הקובץ בלוג העדכני ביותר)
curl -s -u "$CREDS" "https://jewishcoach-api.scm.azurewebsites.net/api/vfs/LogFiles/2026_02_24_lw0sdlwk0008YP_default_docker.log" | grep "BSD"
```

## איך לבדוק לוגים ידנית

### אפשרות 1: Log Stream ב-Azure Portal

1. היכנס ל-[Azure Portal](https://portal.azure.com)
2. חפש **jewishcoach-api** (App Service)
3. בתפריט השמאלי: **Monitoring** → **Log stream**
4. הפעל שיחה חדשה וצפה בלוגים בזמן אמת

### אפשרות 2: SSH Console

1. גלוש ל: https://jewishcoach-api.scm.azurewebsites.net/webssh/host
2. הרץ:
```bash
cd /home/LogFiles
ls -la
tail -500 application.log   # או python*.log, stdout*.log
```

### אפשרות 3: הורדת לוגים (CLI)

```bash
az login
az webapp log download \
  --name jewishcoach-api \
  --resource-group jewish-coach-rg \
  --log-file ./azure_logs.zip
```

אחרי ההורדה – לפתוח את הקובץ ולחפש:
- `[BSD V2]` – לוגים כלליים
- `[Safety Net]` – Safety Net
- `REPETITION_RULE` / `REPETITION_OVERRIDE` – זיהוי חזרות
- `TRANSITION_BLOCK` / `TRANSITION_ATTEMPT` – מעברי שלבים
- `LLM_DECISION` – החלטת המודל (step, saturation)

### אפשרות 4: Application Insights (אם מוגדר)

אם יש Application Insights מחובר:
1. Azure Portal → **Application Insights** → **Logs**
2. שאילתה לדוגמה:
```kusto
traces
| where timestamp > ago(1d)
| where message contains "[BSD" or message contains "Safety Net" or message contains "REPETITION"
| order by timestamp desc
| take 200
```

## מה לחפש בלוגים (בהקשר ללולאת S1)

| תוכן לוג | משמעות |
|----------|--------|
| `REPETITION_RULE | rule=generic_patterns` | Safety Net זיהה חפירה חוזרת |
| `REPETITION_OVERRIDE` | הוחלפה תשובת המאמן |
| `Too many generic questions` | זיהוי לולאת חפירה |
| `LLM_DECISION | step=S1` | המודל נשאר ב-S1 |
| `TRANSITION_BLOCK | old_step=S1, new_step=S2` | חסימת מעבר ל-S2 |
| `Safety Net] DISABLED` | Safety Net כבוי |

---

## ממצאים משיחה 60 (זוגיות, הבעת רגשות) – 25.2.2026

| זמן | משתמש | מאמן | Step |
|-----|-------|------|------|
| 05:30 | על הבעת רגשות, אני מרגיש חסום | תוכל לספר לי יותר על מה בדיוק... | S1 |
| 05:31 | אני רוצה להתאמן על להיות יותר משוחרר בהבעת רגשות | תוכל לספר לי יותר על מה בדיוק מרגיש לך חסום... | S1 |
| 05:31 | אני לא מצליח לבטא רגשות בזוכיות | תוכל לספר לי יותר... | S1 |
| 05:31 | הבעת רגשות, אני מרגיש חסום | רגע, לפני שנדבר על רגשות - בוא ניקח אירוע ספציפי... ש[נושא] | S1 |

### סיבת השורש

1. **המודל לא מחזיר JSON** – בכל תור: `[BSD V2] Failed to parse JSON`. המודל מחזיר טקסט רגיל במקום JSON.
2. **Safety Net עבד** – "Too many generic questions (3)", "Overriding repeated question", "BLOCKED S1→S3".
3. **Placeholder [נושא]** – הודעת התיקון הכילה [נושא] שלא הוחלף. תוקן: חילוץ topic מהיסטוריה (דילוג על "מה שמך?", "שלום").

### תיקונים שבוצעו

- חילוץ topic: דילוג על "מה שמך?", "שלום" – העדפת הודעות נושא (len >= 10).
- החלפת [נושא]: דילוג על greetings גם בבלוק ההחלפה.
- שמירת collected_data ב-fallback: כשהמודל לא מחזיר JSON, שומרים collected_data מהמצב הקודם.

### אם המודל לא מחזיר JSON – בדוק ב-Azure

| הגדרה | ערך מומלץ | הסבר |
|-------|-----------|------|
| `AZURE_OPENAI_API_VERSION` | `2024-08-01-preview` | נדרש ל-Structured Output. |
| `BSD_V2_STRUCTURED_OUTPUT` | `1` | מפעיל with_structured_output. |
| `BSD_V2_STRUCTURED_STRICT` | `0` | אם יש שגיאה – נסה 0. |
| `BSD_V2_JSON_MODE` | `1` | Fallback – response_format json_object. |

אם שני המצבים נכשלים – המודל מתעלם מההוראות. נסה `USE_GEMINI=1` + `GOOGLE_API_KEY` ל-A/B test.

---

## ממצאים משיחה 59 (הורות, הצבת גבולות) – 24.2.2026

| זמן | משתמש | מאמן | Step |
|-----|-------|------|------|
| 16:03 | כן | מעולה, תודה שאישרת... על מה תרצה להתאמן? | S0 |
| 16:04 | הורות | כשאתה אומר 'הורות', על מה בדיוק אתה מתכוון? | S1 |
| 16:04 | בהצבת גבולות לילדים | ספר לי יותר... מה בזה מעסיק אותך? | S1 |
| 16:05 | היכולת להציב גבול אפקטיבי | מה בדיוק היית רוצה לשפר או לשנות? | S1 |
| 16:05 | להציב גבול, ולעמוד מאחוריו | על איזה היבט היית רוצה להתמקד? | S1 |
| 16:05 | על הצבת גבול | אני מבין... מה בדיוק היית רוצה לשפר בהצבת הגבול? | S1 |
| 16:06 | להציב גבול, ולעמוד מאחוריו | תוכל לשתף באירוע ספציפי... מתי זה קרה? | S1 |

### סיבת השורש

1. **המודל לא מחזיר JSON** – בכל תור: `[BSD V2] Failed to parse JSON: Could not parse model JSON payload`. המודל מחזיר טקסט רגיל במקום JSON מובנה.
2. **Safety Net לא רץ / לא תפס** – אין לוגים של `REPETITION_OVERRIDE` או `generic_patterns`. ייתכן שרמת הלוגים ב-Azure מסננת אותם.
3. **המודל נשאר ב-S1** – ללא JSON, `current_step` נשאר מהמצב הקודם (S1) ולא מתעדכן ל-S2.

### תיקונים שבוצעו

- הוספת דפוסים: "על איזה היבט", "מה בדיוק היית רוצה"
- מעבר ל-S2 בעת override של לולאת חפירה
- חיזוק הפרומפט: "אחרי 2+ הודעות עם נושא ברור – עבור ל-S2 מיד"

---

## הפעלת לוגים (אם לא מופעלים)

ב-Azure Portal → jewishcoach-api → **App Service logs**:
- **Application Logging (Filesystem)**: On
- **Application Logging (Blob)**: אופציונלי
- **Log Level**: Information
- **Web server logging**: On
