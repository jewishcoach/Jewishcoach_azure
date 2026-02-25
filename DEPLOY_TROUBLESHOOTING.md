# פתרון בעיות פריסה ל-Azure

## הבעיה
- `/api/chat/v2/warmup` ו-`/api/chat/v2/message/stream` מחזירים 404
- השרת מריץ גרסה ישנה (commit bffadaa)
- פריסה ישירה (`az webapp deploy`) נכשלת עם 503

## מה נעשה
1. **עדכון deploy_to_azure.sh** – הוספת `--enable-kudu-warmup false`, `--async true`, `--restart true`
2. **הפריסה עדיין נכשלת** – 503 מ-Kudu (שירות הפריסה)

## צעדים לפתרון

### 1. הרצת פריסה מ-GitHub Actions
- GitHub → **Actions** → **Deploy Backend to Azure Web App** → **Run workflow**
- אם הפריסה מצליחה – הבעיה היא ברשת/סביבה המקומית

### 2. בדיקת Azure Portal
- **jewishcoach-api** → **Deployment Center** → לוודא שמקור הפריסה תקין
- **Diagnose and solve problems** → לבדוק שגיאות 503
- **Configuration** → **Application settings** → לוודא שאין הגדרות שמפריעות

### 3. vNet Integration (אם מופעל)
- אם יש vNet integration – ייתכן שהוא חוסם את Kudu
- נסה לכבות זמנית: **Networking** → **VNet integration** → **Disconnect**

### 4. Restart ידני
```bash
az webapp restart --name jewishcoach-api --resource-group jewish-coach-rg
```

### 5. פריסה מקומית (אם az login עובד)
```bash
cd backend
./deploy_to_azure.sh
```

### 6. שגיאת 409 Conflict בפריסה
- **סיבה:** פריסה קודמת עדיין רצה, או נעילות ב-Kudu
- **פתרון אוטומטי:** ה-workflow מחכה 2 דקות בהתחלה, ואז 3 ניסיונות פריסה (המתנה 3 דקות בין ניסיונות)
- **פתרון ידני (מומלץ):**
  1. **Restart:** Azure Portal → jewishcoach-api → Overview → **Restart**
  2. חכה 2–3 דקות
  3. GitHub → Actions → **Re-run** את ה-workflow
- **פתרון קבוע:** הוסף secret `AZURE_CREDENTIALS` (Service Principal) – ה-workflow יריץ Restart אוטומטית לפני כל פריסה. [הוראות](https://github.com/Azure/login#configure-a-service-principal-with-a-secret)

## Fallback – הצ'אט עובד בלי streaming
- `/api/chat/v2/message` (POST) קיים ומחזיר 401 כשאין auth
- כשמחוברים – הצ'אט עובד ב-non-streaming mode
- warmup הוא best-effort – האפליקציה ממשיכה גם כשהוא נכשל
