# 🎭 Demo Mode - פעיל!

## מה עשיתי:

### 1️⃣ Backend (Python)
✅ הוספתי **Demo Mode** ב-`dependencies.py`:
- כשבקשה מגיעה מ-tunnel domain (`.lhr.life`, `.ngrok-free.app`)
- הבאקאנד יוצר/משתמש במשתמש דמו בשם `demo@tunnel.test`
- **אין צורך ב-Clerk authentication** מ-tunnel domains

### 2️⃣ Frontend (React/TypeScript)
✅ הוספתי **Demo Mode** ב-`App.tsx`:
- כשהאפליקציה רצה על tunnel domain
- דולג על Clerk login
- מציג ישירות את `ChatInterface` עם "Demo User"
- תג "DEMO MODE" צהוב בכותרת

### 3️⃣ CORS
✅ עדכנתי את `main.py`:
- מאפשר `*.lhr.life` (localhost.run)
- מאפשר `*.ngrok-free.app`
- מאפשר `*.localhost.run`

---

## 🌐 קישורים פעילים:

```
🎨 Frontend (Demo Mode):
https://9a8baf8405c233.lhr.life

⚙️ Backend API:
https://cea58aff2e076f.lhr.life
```

---

## ✅ מה המשתמש המרוחק אמור לראות עכשיו:

1. **פותח את הקישור**: https://9a8baf8405c233.lhr.life
2. **רואה את האפליקציה** עם תג "DEMO MODE" צהוב בפינה
3. **יכול לשלוח הודעות** מיד, ללא התחברות
4. **הסוכן מגיב** כרגיל

---

## 📝 הגדרות סביבה (כבר מוגדרות):

Backend `.env`:
```bash
ALLOW_TUNNELS=true        # מאפשר tunnel domains
ALLOW_DEMO_MODE=true      # מאפשר demo user ללא Clerk
```

Frontend `.env.local`:
```bash
VITE_API_URL=https://cea58aff2e076f.lhr.life/api
```

---

## ⚠️ חשוב:

- **Demo Mode הוא זמני** - מיועד לבדיקות בלבד
- **אין persistent data** - המשתמש הוא demo user משותף
- **לפרודקשן** - צריך Clerk authentication תקין

---

## 🔍 איך לבדוק שזה עובד:

### ב-Browser Console (F12):
```
✅ צריך לראות:
🎭 [DEMO MODE] Running in tunnel demo mode - authentication bypassed
```

### ב-Backend Logs:
```
✅ צריך לראות:
🎭 [DEMO MODE] Request from tunnel domain: https://9a8baf8405c233.lhr.life
✅ [DEMO MODE] Created demo user for tunnel testing
```

---

## 🚀 סטטוס:

| רכיב | סטטוס | הערות |
|------|-------|-------|
| Frontend | ✅ DEMO MODE | דולג על Clerk |
| Backend | ✅ DEMO MODE | משתמש דמו |
| CORS | ✅ מוגדר | tunnel domains |
| Tunnels | ✅ פעילים | localhost.run |

---

**כל המערכת מוכנה!** 🎉

שלח למשתמש המרוחק:
```
היי! כנס לקישור:
https://9a8baf8405c233.lhr.life

זה במצב דמו - תוכל להתחיל לשלוח הודעות מיד!
```




