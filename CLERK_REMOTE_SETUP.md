# 🔐 הוספת Doman ל-Clerk לגישה מרחוק

## הבעיה:
המשתמש המרוחק רואה את האפליקציה אבל הסוכן לא מגיב כי Clerk חוסם את הדומיין החדש.

## הפתרון:

### 1️⃣ היכנס ל-Clerk Dashboard
🔗 https://dashboard.clerk.com

### 2️⃣ בחר את הפרויקט שלך
"Jewish Coach" או הפרויקט הרלוונטי

### 3️⃣ עבור ל-Settings
`Configure` → `Domains` או `Settings` → `Development`

### 4️⃣ הוסף דומיין
במצב **Development**, Clerk אמור לאפשר אוטומטית כל דומיין.

אם זה לא עובד, הוסף ידנית:
```
https://9a8baf8405c233.lhr.life
```

או באופן גנרי (wildcard):
```
https://*.lhr.life
```

### 5️⃣ שמור ורענן
- לחץ **Save**
- רענן את הדף במחשב המרוחק (F5)
- נסה שוב לשלוח הודעה

---

## 📝 URL הנוכחי:
- **Frontend**: https://9a8baf8405c233.lhr.life
- **Backend**: https://cea58aff2e076f.lhr.life

---

## 🔍 בדיקה:
אם המשתמש רואה את מסך ההתחברות של Clerk - זה סימן טוב!
אם הוא מחובר אבל הצ'אט לא עובד - בדוק ש-Development Mode מופעל ב-Clerk.

---

## 🚨 אם זה לא עובד:

### פתרון חלופי: Disable Authentication זמנית
**⚠️ רק לבדיקות!**

במקום זה, אפשר להריץ את הבאקאנד ללא Clerk authentication בדומיינים של tunnels.

נצטרך לשנות את `backend/app/dependencies.py` להחריג tunneling domains.




