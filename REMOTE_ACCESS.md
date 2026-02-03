# 🌐 גישה מרחוק למערכת

המערכת כבר מוכנה לגישה מרחוק! ✅

## כיצד להפעיל:

### 1️⃣ התקן Ngrok (אם עוד לא מותקן)
```bash
# הורד מ: https://ngrok.com/download
# או דרך apt/brew:
snap install ngrok
# או
brew install ngrok
```

### 2️⃣ התחבר לחשבון Ngrok
```bash
ngrok authtoken YOUR_TOKEN
# קבל את ה-token מ: https://dashboard.ngrok.com/get-started/your-authtoken
```

### 3️⃣ הרץ Ngrok tunnel לבאקאנד
```bash
ngrok http 8000
```

זה ייתן לך URL כמו:
```
https://abc123.ngrok-free.app -> http://localhost:8000
```

### 4️⃣ עדכן את הפרונטאנד להצביע ל-Ngrok URL

ערוך את `frontend/.env.local`:
```bash
VITE_API_URL=https://abc123.ngrok-free.app/api
```

### 5️⃣ הרץ מחדש את הפרונטאנד
```bash
cd frontend
npm run dev
```

---

## ✅ מה כבר מוכן:

- **CORS מוגדר** - מאפשר `*.ngrok-free.app`
- **Backend רץ** - על פורט 8000
- **Frontend רץ** - על פורט 5173

---

## 🚀 שימוש מהיר:

### Terminal 1 - Backend (כבר רץ)
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2 - Ngrok
```bash
ngrok http 8000
```
📋 העתק את ה-URL (https://xxx.ngrok-free.app)

### Terminal 3 - Frontend
```bash
cd frontend
echo "VITE_API_URL=https://xxx.ngrok-free.app/api" > .env.local
npm run dev
```

---

## 🔍 בדיקה:

1. פתח `https://xxx.ngrok-free.app/docs` בדפדפן
2. אמור לראות את Swagger UI של FastAPI
3. גש ל-`http://localhost:5173` - הפרונטאנד יתחבר לבאקאנד דרך Ngrok

---

## 💡 טיפים:

- **Ngrok חינמי**: מוגבל ל-1 tunnel בו-זמנית
- **URL משתנה**: בכל הפעלה מחדש של ngrok ה-URL משתנה
- **Production**: לסביבת ייצור עדיף להשתמש ב-Azure/AWS במקום Ngrok

---

**Status**: ✅ Ready to use!




