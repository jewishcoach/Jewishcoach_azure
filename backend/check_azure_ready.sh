#!/bin/bash

# Jewish Coach Backend - Azure Deployment Readiness Check
# This script checks if all requirements are met for Azure deployment

set -e

echo "🔍 Jewish Coach Backend - Azure Deployment Readiness Check"
echo "============================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅${NC} $1 exists"
        return 0
    else
        echo -e "${RED}❌${NC} $1 NOT FOUND"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Function to check if string exists in file
check_in_file() {
    if grep -q "$2" "$1" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} Found '$2' in $1"
        return 0
    else
        echo -e "${YELLOW}⚠️${NC}  '$2' not found in $1"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

# Function to check environment variable
check_env() {
    if [ -n "${!1}" ]; then
        echo -e "${GREEN}✅${NC} $1 is set"
        return 0
    else
        echo -e "${YELLOW}⚠️${NC}  $1 is NOT set (required for Azure)"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

echo "📁 Checking critical files..."
echo "------------------------------"
check_file "startup.sh"
check_file "web.config"
check_file "requirements.txt"
check_file "requirements-azure.txt"
check_file "app/main.py"
check_file "app/database.py"
echo ""

echo "📦 Checking dependencies in requirements.txt..."
echo "------------------------------------------------"
check_in_file "requirements.txt" "fastapi"
check_in_file "requirements.txt" "uvicorn"
check_in_file "requirements.txt" "gunicorn"
check_in_file "requirements.txt" "sqlalchemy"
check_in_file "requirements.txt" "openai"
check_in_file "requirements.txt" "langchain"
check_in_file "requirements.txt" "psycopg2-binary"
check_in_file "requirements.txt" "requests"
echo ""

echo "🔧 Checking startup.sh configuration..."
echo "----------------------------------------"
check_in_file "startup.sh" "gunicorn"
check_in_file "startup.sh" "uvicorn.workers.UvicornWorker"
check_in_file "startup.sh" "PYTHONPATH"
check_in_file "startup.sh" "PORT"
check_in_file "startup.sh" "timeout"
echo ""

echo "📄 Checking web.config..."
echo "-------------------------"
check_in_file "web.config" "httpPlatform"
check_in_file "web.config" "startup.sh"
check_in_file "web.config" "stdoutLogEnabled"
echo ""

echo "🔐 Checking environment variables (local)..."
echo "--------------------------------------------"
echo "Note: These should be set in Azure App Service Configuration"
check_env "AZURE_OPENAI_API_KEY"
check_env "AZURE_OPENAI_ENDPOINT"
check_env "AZURE_OPENAI_DEPLOYMENT_NAME"
echo ""

echo "🏥 Testing health check endpoint..."
echo "-----------------------------------"
if python -c "from app.main import app; print('✅ app.main imports successfully')" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} FastAPI app imports successfully"
else
    echo -e "${RED}❌${NC} Failed to import FastAPI app"
    ERRORS=$((ERRORS + 1))
fi
echo ""

echo "🗄️  Testing database connection..."
echo "----------------------------------"
if python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine); print('✅ Database OK')" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} Database connection successful"
else
    echo -e "${YELLOW}⚠️${NC}  Database connection failed (may be normal if using Azure PostgreSQL)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

echo "============================================================"
echo "📊 Summary"
echo "============================================================"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 Perfect! Everything looks good!${NC}"
    echo ""
    echo "✅ All critical files exist"
    echo "✅ All dependencies are listed"
    echo "✅ Configuration files are correct"
    echo ""
    echo "🚀 Ready to deploy to Azure!"
    echo ""
    echo "Next steps:"
    echo "1. Ensure environment variables are set in Azure Portal"
    echo "2. git add . && git commit -m 'fix: Azure deployment ready'"
    echo "3. git push origin main"
    echo "4. Monitor GitHub Actions and Azure logs"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Almost ready with $WARNINGS warning(s)${NC}"
    echo ""
    echo "Warnings are usually about environment variables."
    echo "Make sure to set them in Azure App Service Configuration."
    echo ""
    echo "🟡 You can proceed with deployment, but check warnings above."
    exit 0
else
    echo -e "${RED}❌ Found $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    echo ""
    echo "Please fix the errors above before deploying."
    echo ""
    echo "See AZURE_DEPLOYMENT_TROUBLESHOOTING.md for help."
    exit 1
fi
