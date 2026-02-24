# הוספת AZURE_CREDENTIALS ל-GitHub Secrets

**AZURE_CREDENTIALS** מאפשר ל-GitHub Actions לבצע restart לאפליקציה לפני deploy – מפחית שגיאות 409 Conflict.

## שלב 1: התחברות ל-Azure CLI

```bash
az login
```

## שלב 2: קבלת Subscription ID

```bash
az account show --query id -o tsv
```

העתק את ה-ID (מחרוזת כמו `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).

## שלב 3: יצירת Service Principal

הרץ (החלף `YOUR_SUBSCRIPTION_ID` ב-ID שקיבלת):

```bash
az ad sp create-for-rbac \
  --name "github-jewishcoach-deploy" \
  --role contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/jewish-coach-rg \
  --sdk-auth
```

**או** השתמש בסקריפט הקיים:

```bash
cd backend
./setup_azure_credentials.sh
```

הפקודה תחזיר JSON – **העתק את כל ה-JSON**.

## שלב 4: הוספה ל-GitHub Secrets

1. עבור ל־**GitHub** → **jewishcoach/Jewishcoach_azure**
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret**
4. **Name:** `AZURE_CREDENTIALS`
5. **Value:** הדבק את כל ה-JSON מהשלב 3
6. **Add secret**

## אימות

אחרי הוספת ה-secret, ה-workflow יוכל:
- לבצע `az login` עם ה-credentials
- להריץ `az webapp restart` לפני deploy
- להקטין 409 Conflict

---

## הגדרות Azure App Settings (חובה)

### דרך CLI

```bash
az webapp config appsettings set \
  --name jewishcoach-api \
  --resource-group jewish-coach-rg \
  --settings BSD_V2_JSON_MODE=1
```

### דרך Portal

ב-**Azure Portal** → **jewishcoach-api** → **Configuration** → **Application settings**:

| משתנה | ערך | הסבר |
|-------|-----|------|
| `BSD_V2_STRUCTURED_OUTPUT` | `1` (ברירת מחדל) | Structured Outputs (Pydantic + json_schema) – ה-API לא יכול להחזיר JSON לא תקין. מומלץ מאוד. |
| `BSD_V2_STRUCTURED_STRICT` | `1` (ברירת מחדל) | strict=True ב-json_schema. אם Azure מחזיר שגיאה – הגדר ל-0. |
| `AZURE_OPENAI_API_VERSION` | `2024-08-01-preview` | נדרש ל-Structured Outputs. אם חסר – ייפול ל-JSON Mode (עובד). |
| `BSD_V2_JSON_MODE` | `1` | משמש fallback כש-Structured Output נכשל. מפעיל `response_format={"type": "json_object"}`. |

---

## A/B Testing: Google Gemini (USE_GEMINI=1)

כדי להפעיל את מנוע Gemini במקום Azure OpenAI:

| משתנה | ערך | הסבר |
|-------|-----|------|
| `USE_GEMINI` | `1` | מפעיל את מנוע Google Gemini (gemini-1.5-flash) במקום Azure. |
| `GOOGLE_API_KEY` | `...` | **חובה** כש-USE_GEMINI=1. API key מ-[Google AI Studio](https://aistudio.google.com/apikey). |

הגדרות Gemini מותאמות לאימון/בריאות נפשית: חסימת safety מושבתת כדי לאפשר למשתמשים להביע רגשות שליליים בחופשיות.

---

**הערה:** ה-secret לא מוצג שוב אחרי השמירה. אם צריך לעדכן – מחק את ה-secret הקיים ויצור חדש.
