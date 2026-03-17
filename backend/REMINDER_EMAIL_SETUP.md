# תזכורות במייל – הגדרה

## סקירה
המערכת שולחת תזכורות במייל למשתמשים כשמגיע זמן האימון.
השולח: `reminders@jewishcoacher.com`

## אפשרויות (בסדר עדיפות)

### 1. Azure Communication Services Email (מומלץ)
- משאב Azure Communication Services מחובר ל-Email Domain
- **Azure Managed Domain** (ברירת מחדל): שולח מ-`donotreply@xxx.azurecomm.net`
- **דומיין מותאם** `jewishcoacher.com`: דורש אימות (ראה [Connect a verified email domain](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/email/connect-email-communication-resource))
- משתני סביבה:
  ```bash
  EMAIL_CONNECTION_STRING=endpoint=https://xxx.communication.azure.com/;accessKey=xxx
  EMAIL_SENDER=donotreply@xxx.azurecomm.net  # חובה עבור Azure Managed Domain
  ```

### 2. SendGrid (חלופה)
- חשבון ב-[SendGrid](https://sendgrid.com)
- אימות דומיין `jewishcoacher.com` (SPF, DKIM)
- משתנה סביבה:
  ```bash
  SENDGRID_API_KEY=SG.xxxx...
  ```

### 3. משתנה סביבה משותף
```bash
REMINDER_CRON_SECRET=your-secret-for-cron  # להגנה על ה-endpoint
```

## הגדרה ב-Azure Portal

1. עבור ל-**Azure Portal** → **jewishcoach-api** → **Configuration** → **Application settings**
2. הוסף:
   - **EMAIL_CONNECTION_STRING** – Connection string מ-Azure Communication Services (משאב Email)
   - **REMINDER_CRON_SECRET** – מחרוזת סודית להגנת ה-endpoint
3. שמור (Save) והפעל מחדש את האפליקציה

**או דרך Azure CLI:**
```bash
az webapp config appsettings set \
  --name jewishcoach-api \
  --resource-group jewish-coach-rg \
  --settings \
    EMAIL_CONNECTION_STRING="endpoint=https://YOUR-RESOURCE.communication.azure.com/;accessKey=YOUR_KEY" \
    REMINDER_CRON_SECRET="$(openssl rand -hex 24)"
```

**סקריפט מהיר:**
```bash
EMAIL_CONNECTION_STRING="endpoint=..." REMINDER_CRON_SECRET="..." ./scripts/set_azure_email_settings.sh
```

## קריאה ל-endpoint

**POST** `/api/calendar/send-reminder-emails`

**Header:** `X-Cron-Secret: <REMINDER_CRON_SECRET>`

### Azure Logic Apps
1. יצירת Logic App עם Trigger: Recurrence (כל 15 דקות)
2. פעולה: HTTP – POST ל-`https://jewishcoach-api.azurewebsites.net/api/calendar/send-reminder-emails`
3. Headers: `X-Cron-Secret` = הערך מ-REMINDER_CRON_SECRET

### cURL (לבדיקה)
```bash
curl -X POST "https://jewishcoach-api.azurewebsites.net/api/calendar/send-reminder-emails" \
  -H "X-Cron-Secret: YOUR_SECRET"
```

## לוגיקה
- רץ כל 15 דקות
- שולח תזכורות שהמועד שלהן בתוך חלון של 15 דקות אחורה עד 5 דקות קדימה
- מעדכן `last_sent` אחרי שליחה
- תזכורת חד-פעמית: נשלחת פעם אחת
- תזכורת חוזרת: נשלחת שוב רק אחרי שעה מהשליחה הקודמת
