#!/bin/bash

# Ngrok Environment Setup Helper
# This script helps you quickly set up .env files for Ngrok testing

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║             Ngrok Tunnel Setup Helper                       ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Frontend .env.development (local)
if [ ! -f "frontend/.env.development" ]; then
    echo "📝 Creating frontend/.env.development (local dev)..."
    cat > frontend/.env.development << 'ENVDEV'
# Development Environment (Local)
VITE_API_URL=http://localhost:8000/api
ENVDEV
    echo "✅ Created frontend/.env.development"
else
    echo "✅ frontend/.env.development already exists"
fi

# Frontend .env.tunnel (template)
if [ ! -f "frontend/.env.tunnel" ]; then
    echo "📝 Creating frontend/.env.tunnel (template)..."
    cat > frontend/.env.tunnel << 'ENVTUNNEL'
# Tunnel Environment (Ngrok)
# Replace the URL below with your actual Ngrok backend URL
VITE_API_URL=https://YOUR-BACKEND-ID.ngrok-free.app/api
ENVTUNNEL
    echo "✅ Created frontend/.env.tunnel"
    echo "⚠️  IMPORTANT: Edit frontend/.env.tunnel and replace with your actual Ngrok backend URL!"
else
    echo "✅ frontend/.env.tunnel already exists"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📖 Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Start your backend for Ngrok:"
echo "   cd backend"
echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "2. In a new terminal, expose backend via Ngrok:"
echo "   ngrok http 8000"
echo ""
echo "3. Copy the Ngrok HTTPS URL (e.g., https://abc123.ngrok-free.app)"
echo ""
echo "4. Update frontend/.env.tunnel with your Ngrok backend URL:"
echo "   nano frontend/.env.tunnel"
echo "   (or use your favorite editor)"
echo ""
echo "5. Start frontend with tunnel config:"
echo "   cd frontend"
echo "   npm run dev -- --mode tunnel"
echo ""
echo "6. In a new terminal, expose frontend via Ngrok:"
echo "   ngrok http 5173"
echo ""
echo "7. Share the frontend Ngrok URL for external testing! 🎉"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 See NGROK_SETUP.md for detailed instructions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

