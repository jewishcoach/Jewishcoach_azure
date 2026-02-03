# 🚀 Azure Deployment Guide - Jewish Coach App

## 📋 Overview

This guide will help you deploy the entire Jewish Coach application to Azure:
- **Backend**: Azure App Service (FastAPI)
- **Frontend**: Azure Static Web Apps (React)
- **Database**: SQLite (can upgrade to Azure SQL later)
- **AI**: Azure OpenAI (already configured)

---

## 🎯 Prerequisites

✅ Azure account with active subscription
✅ GitHub account (for CI/CD)
✅ Azure CLI installed
✅ Git repository for the project

---

## 📦 Step 1: Create Azure Resources

### Option A: Using Azure Portal (Recommended for beginners)

#### 1.1 Create Backend App Service

1. Go to [Azure Portal](https://portal.azure.com)
2. Click "Create a resource" → "Web App"
3. Configure:
   - **Name**: `jewishcoach-api` (or your preferred name)
   - **Runtime**: Python 3.12
   - **Region**: East US (same as OpenAI)
   - **Pricing**: B1 Basic ($13/month) or F1 Free (for testing)
4. Click "Review + Create" → "Create"

#### 1.2 Create Frontend Static Web App

1. Click "Create a resource" → "Static Web App"
2. Configure:
   - **Name**: `jewishcoach-frontend`
   - **Region**: East US 2
   - **Plan**: Free (for testing) or Standard ($9/month)
   - **Build Details**: Skip for now (we'll configure via GitHub Actions)
3. Click "Review + Create" → "Create"

---

### Option B: Using Azure CLI (Faster!)

```bash
# Login to Azure
az login

# Set variables
RESOURCE_GROUP="jewish-coach-rg"
LOCATION="eastus"
BACKEND_NAME="jewishcoach-api"
FRONTEND_NAME="jewishcoach-frontend"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create App Service Plan
az appservice plan create \
  --name ${BACKEND_NAME}-plan \
  --resource-group $RESOURCE_GROUP \
  --sku B1 \
  --is-linux

# Create Web App for Backend
az webapp create \
  --name $BACKEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan ${BACKEND_NAME}-plan \
  --runtime "PYTHON:3.12"

# Create Static Web App for Frontend
az staticwebapp create \
  --name $FRONTEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --location eastus2
```

---

## 🔐 Step 2: Configure Environment Variables

### 2.1 Backend Configuration

In Azure Portal → Your App Service → Configuration → Application settings:

```
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_ENDPOINT=https://eastus.api.cognitive.microsoft.com/
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small

AZURE_SEARCH_SERVICE_ENDPOINT=<your-search-endpoint>
AZURE_SEARCH_INDEX_NAME=jewish-coaching-index
AZURE_SEARCH_ADMIN_KEY=<your-search-key>

SECRET_KEY=<generate-random-32-char-string>
DATABASE_URL=sqlite:///./jewish_coach.db

# Optional: If using Clerk for auth
CLERK_SECRET_KEY=<your-clerk-secret>
```

**To generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2.2 Frontend Configuration

In Azure Portal → Static Web App → Configuration:

```
VITE_API_URL=https://jewishcoach-api.azurewebsites.net/api
VITE_CLERK_PUBLISHABLE_KEY=<your-clerk-public-key>
```

---

## 🔗 Step 3: Setup GitHub CI/CD

### 3.1 Get Azure Publish Profiles

#### For Backend:
1. Azure Portal → Your App Service → Download publish profile
2. Save the content

#### For Frontend:
1. Azure Portal → Static Web App → Manage deployment token
2. Copy the token

### 3.2 Add GitHub Secrets

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Add these secrets:

```
AZURE_WEBAPP_PUBLISH_PROFILE=<backend-publish-profile-content>
AZURE_STATIC_WEB_APPS_API_TOKEN=<frontend-deployment-token>
VITE_API_URL=https://jewishcoach-api.azurewebsites.net/api
VITE_CLERK_PUBLISHABLE_KEY=<your-clerk-key>
```

---

## 🚀 Step 4: Deploy!

### 4.1 Initial Manual Deploy (Backend)

```bash
cd backend

# Install Azure CLI extension
az extension add --name webapp

# Deploy
az webapp up \
  --name jewishcoach-api \
  --resource-group jewish-coach-rg \
  --runtime "PYTHON:3.12"
```

### 4.2 Initial Manual Deploy (Frontend)

```bash
cd frontend

# Build
npm install
npm run build

# Deploy via Azure Static Web Apps CLI
npm install -g @azure/static-web-apps-cli
swa deploy ./dist \
  --deployment-token <your-token>
```

### 4.3 Automatic Deploys (GitHub Actions)

The GitHub Actions workflows are already configured!

**Now every push to `main` will automatically deploy:**
- Backend changes → Azure App Service
- Frontend changes → Azure Static Web Apps

---

## ✅ Step 5: Verify Deployment

### Backend Health Check:
```bash
curl https://jewishcoach-api.azurewebsites.net/api/health
# Expected: {"status":"healthy"}
```

### Frontend:
Visit: `https://jewishcoach-frontend.azurestaticapps.net`

---

## 🔧 Step 6: Database Migration (Optional)

If you want to use Azure SQL instead of SQLite:

### Create Azure SQL Database:
```bash
az sql server create \
  --name jewishcoach-sql \
  --resource-group jewish-coach-rg \
  --location eastus \
  --admin-user adminuser \
  --admin-password <strong-password>

az sql db create \
  --name jewishcoach-db \
  --server jewishcoach-sql \
  --resource-group jewish-coach-rg \
  --service-objective S0
```

### Update DATABASE_URL:
```
DATABASE_URL=postgresql://adminuser:<password>@jewishcoach-sql.database.windows.net/jewishcoach-db
```

---

## 💰 Cost Estimate

| Service | Plan | Monthly Cost |
|---------|------|--------------|
| App Service (Backend) | B1 Basic | ~$13 |
| Static Web App (Frontend) | Free | $0 |
| Azure SQL Database | Basic | ~$5 |
| Azure OpenAI | Pay-as-you-go | ~$10-50 |
| Azure AI Search | Basic | ~$75 |
| **Total** | | **~$103-143/month** |

**Tips to reduce costs:**
- Use F1 Free tier for App Service (testing only)
- Use SQLite instead of Azure SQL (saves $5)
- Use Free tier for Static Web App

---

## 🐛 Troubleshooting

### Backend not starting:
```bash
# Check logs
az webapp log tail \
  --name jewishcoach-api \
  --resource-group jewish-coach-rg
```

### Frontend not loading API:
- Check CORS settings in backend
- Verify VITE_API_URL is correct
- Check Network tab in browser DevTools

### Database errors:
- Verify SQLite file is writable
- Check DATABASE_URL format
- Run migrations: `alembic upgrade head`

---

## 📊 Monitoring

### Enable Application Insights:
```bash
az monitor app-insights component create \
  --app jewishcoach-insights \
  --location eastus \
  --resource-group jewish-coach-rg \
  --application-type web

# Link to App Service
az webapp config appsettings set \
  --name jewishcoach-api \
  --resource-group jewish-coach-rg \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="<connection-string>"
```

---

## 🎉 Success!

Your app is now live on Azure:
- **Frontend**: `https://jewishcoach-frontend.azurestaticapps.net`
- **Backend**: `https://jewishcoach-api.azurewebsites.net`

Every push to GitHub will automatically deploy updates! 🚀

---

## 📚 Next Steps

1. ✅ Setup custom domain
2. ✅ Configure SSL certificates
3. ✅ Setup monitoring alerts
4. ✅ Implement backup strategy
5. ✅ Setup staging environment

---

*בס״ד - Good luck with your deployment!*
