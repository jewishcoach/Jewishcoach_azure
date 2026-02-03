# Ngrok Tunnel Setup Guide

This guide explains how to expose your app externally for testing using Ngrok.

---

## 🚀 Quick Start

### 1. Install Ngrok (if not already installed)
```bash
# Download from https://ngrok.com/download
# Or via package manager:
brew install ngrok  # macOS
choco install ngrok # Windows
```

### 2. Start Your Backend (Terminal 1)
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Note:** The `--host 0.0.0.0` is important for Ngrok to work!

### 3. Expose Backend via Ngrok (Terminal 2)
```bash
ngrok http 8000
```

**Copy the HTTPS URL** (e.g., `https://abc123.ngrok-free.app`)

### 4. Configure Frontend Environment

Create `frontend/.env.tunnel`:
```env
VITE_API_URL=https://abc123.ngrok-free.app/api
```

*(Replace `abc123` with your actual Ngrok subdomain)*

### 5. Start Frontend with Tunnel Config (Terminal 3)
```bash
cd frontend
npm run dev -- --mode tunnel
```

### 6. Expose Frontend via Ngrok (Terminal 4)
```bash
# In a new terminal
ngrok http 5173
```

**Copy the Frontend HTTPS URL** and share it for testing!

---

## 📁 Environment Files

### Frontend: `.env.development` (Local Dev)
```env
VITE_API_URL=http://localhost:8000/api
```

### Frontend: `.env.tunnel` (Ngrok Testing)
```env
VITE_API_URL=https://YOUR-BACKEND-ID.ngrok-free.app/api
```

*(Replace `YOUR-BACKEND-ID` with your actual Ngrok backend URL)*

---

## 🔧 Backend CORS Configuration

The backend is now configured to automatically allow Ngrok domains!

**Environment Variable (optional):**
Add to `backend/.env` if you want to disable Ngrok in production:
```env
ALLOW_NGROK=true  # Default: true
```

**How it works:**
- The backend uses `allow_origin_regex=r"https://.*\.ngrok-free\.app"` to match any Ngrok domain
- When the app starts, you'll see: `✅ CORS: Ngrok tunneling enabled (*.ngrok-free.app)`

---

## 📝 Complete Workflow

### For Local Development (No Ngrok)
```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev  # Uses .env.development (localhost)
```

### For External Testing (With Ngrok)
```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Backend Ngrok Tunnel
ngrok http 8000
# Copy URL: https://abc123.ngrok-free.app

# Terminal 3: Update frontend/.env.tunnel
echo 'VITE_API_URL=https://abc123.ngrok-free.app/api' > frontend/.env.tunnel

# Terminal 4: Frontend (with tunnel config)
cd frontend
npm run dev -- --mode tunnel

# Terminal 5: Frontend Ngrok Tunnel
ngrok http 5173
# Copy URL: https://xyz789.ngrok-free.app
# Share this URL for external testing!
```

---

## ⚠️ Ngrok Banner Issue

Ngrok shows a "Visit Site" warning banner on the free plan. To bypass:
1. Users click "Visit Site" on first visit
2. Or upgrade to Ngrok paid plan to remove the banner

---

## 🔍 Troubleshooting

### Issue: "CORS policy: No 'Access-Control-Allow-Origin'"
- **Solution:** Make sure your backend Ngrok URL is correctly set in `frontend/.env.tunnel`
- **Check:** Backend logs should show: `✅ CORS: Ngrok tunneling enabled`

### Issue: Frontend can't reach backend
- **Solution:** Ensure backend is running with `--host 0.0.0.0`
- **Check:** Test backend Ngrok URL directly in browser: `https://abc123.ngrok-free.app/health`

### Issue: Clerk authentication fails
- **Solution:** Add your Ngrok frontend URL to Clerk's allowed domains:
  1. Go to Clerk Dashboard → Settings → Domains
  2. Add your Ngrok frontend URL (e.g., `https://xyz789.ngrok-free.app`)

---

## 🎯 Quick Commands Reference

```bash
# Start backend for Ngrok
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tunnel backend
ngrok http 8000

# Start frontend with tunnel config
npm run dev -- --mode tunnel

# Tunnel frontend
ngrok http 5173
```

---

## ✅ Verification

After setup, verify:
1. Backend Ngrok URL responds: `curl https://abc123.ngrok-free.app/health`
2. Frontend loads in browser: `https://xyz789.ngrok-free.app`
3. Backend logs show: `✅ CORS: Ngrok tunneling enabled`
4. Chat functionality works end-to-end

---

**Note:** Ngrok URLs change every time you restart Ngrok (unless you have a paid plan with reserved domains).
Remember to update `frontend/.env.tunnel` each time!




