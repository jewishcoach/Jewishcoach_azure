# Quick Ngrok Reference Card

## 🚀 5-Terminal Setup

### Terminal 1: Backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Backend Ngrok
```bash
ngrok http 8000
```
**→ Copy the HTTPS URL**

### Terminal 3: Update Frontend Config
```bash
nano frontend/.env.tunnel
# Paste: VITE_API_URL=https://YOUR-BACKEND-ID.ngrok-free.app/api
```

### Terminal 4: Frontend (Tunnel Mode)
```bash
cd frontend
npm run dev -- --mode tunnel
```

### Terminal 5: Frontend Ngrok
```bash
ngrok http 5173
```
**→ Share this URL!**

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `frontend/.env.development` | Local dev (localhost) |
| `frontend/.env.tunnel` | Ngrok backend URL |
| `backend/app/main.py` | CORS config (auto-allows Ngrok) |
| `NGROK_SETUP.md` | Full documentation |

---

## ✅ Verification Checklist

- [ ] Backend shows: `✅ CORS: Ngrok tunneling enabled`
- [ ] Backend health: `curl https://backend-id.ngrok-free.app/health`
- [ ] Frontend loads in browser
- [ ] Login works
- [ ] Chat sends/receives messages
- [ ] No CORS errors in console

---

## 🔧 Quick Fixes

**CORS Error?**
```bash
# Check frontend/.env.tunnel has correct backend URL
cat frontend/.env.tunnel
```

**Frontend can't connect?**
```bash
# Test backend directly
curl https://YOUR-BACKEND-ID.ngrok-free.app/health
```

**Ngrok timed out?**
```bash
# Restart Ngrok (Terminal 2 & 5)
# Update frontend/.env.tunnel with new URL
# Restart frontend: Terminal 4
```

---

## 🎯 Local Dev (No Ngrok)

```bash
# Terminal 1
cd backend && uvicorn app.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

**That's it!** No config changes needed.




