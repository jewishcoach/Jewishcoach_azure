#!/bin/bash
# Deploy backend to Azure via Zip Deploy
# Usage: ./deploy_to_azure.sh
# Requires: az login, PUBLISH_PROFILE (or az webapp deploy uses its own auth)

set -e
cd "$(dirname "$0")"

echo "📦 Creating deploy zip..."
rm -f deploy.zip
python3 -c "
import zipfile, os
with zipfile.ZipFile('deploy.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for path in ['app', 'requirements.txt', 'startup.sh', 'gunicorn_conf.py', 'web.config']:
        if os.path.isdir(path):
            for r, d, f in os.walk(path):
                for fn in f:
                    if '__pycache__' in r or fn.endswith('.pyc') or 'antenv' in r or 'test_venv' in r:
                        continue
                    z.write(os.path.join(r, fn))
        elif os.path.isfile(path):
            z.write(path)
"

echo "📤 Deploying to Azure..."
if command -v az &>/dev/null; then
  # Ensure Safety Net stays disabled on every deploy; admin RBAC email (must match Clerk primary email)
  echo "⚙️  Setting BSD_V2_SAFETY_NET_DISABLED=1 and ADMIN_EMAIL..."
  az webapp config appsettings set --name jewishcoach-api --resource-group jewish-coach-rg \
    --settings BSD_V2_SAFETY_NET_DISABLED=1 ADMIN_EMAIL=ishai.meisels@gmail.com -o none 2>/dev/null || true

  # Get credentials for zipdeploy (avoids az webapp deploy 503/504 timeouts)
  echo "🔑 Getting deployment credentials..."
  CREDS=$(az webapp deployment list-publishing-profiles --name jewishcoach-api --resource-group jewish-coach-rg \
    --query "[?publishMethod=='MSDeploy'].{user:userName,pass:userPWD}" -o json 2>/dev/null | \
    python3 -c "import sys, json; d=json.load(sys.stdin)[0]; print(f\"{d['user']}:{d['pass']}\")" 2>/dev/null)

  if [ -n "$CREDS" ]; then
    # Use zipdeploy with isAsync=true - returns after upload, no 230s deploy timeout
    echo "📤 Uploading zip (async)..."
    HTTP=$(curl -s -m 180 -o /tmp/deploy_resp.txt -w "%{http_code}" -X POST \
      "https://jewishcoach-api.scm.azurewebsites.net/api/zipdeploy?isAsync=true" \
      -u "$CREDS" \
      -H "Content-Type: application/octet-stream" \
      --data-binary @deploy.zip)
    if [ "$HTTP" = "200" ] || [ "$HTTP" = "202" ]; then
      echo "✅ Zip uploaded successfully (deployment running in background)"
      echo "⏳ Wait 2-5 min for app to restart, then check: curl -s https://jewishcoach-api.azurewebsites.net/health"
    else
      echo "⚠️  zipdeploy returned HTTP $HTTP. Trying az webapp deploy..."
      az webapp deploy --resource-group jewish-coach-rg --name jewishcoach-api \
        --src-path deploy.zip --type zip --enable-kudu-warmup false --async true --restart true || true
    fi
  else
    echo "⚠️  Could not get credentials. Using az webapp deploy..."
    az webapp deploy --resource-group jewish-coach-rg --name jewishcoach-api \
      --src-path deploy.zip --type zip --enable-kudu-warmup false --async true --restart true || true
  fi
else
  echo "⚠️  Azure CLI not found. Using curl (need PUBLISH_PROFILE):"
  if [ -z "$PUBLISH_PROFILE" ]; then
    echo "Run: PUBLISH_PROFILE=\$(az webapp deployment list-publishing-profiles --name jewishcoach-api --resource-group jewish-coach-rg --query \"[?publishMethod=='MSDeploy'].{user:userName,pass:userPWD}\" -o json | python3 -c \"import sys, json; d=json.load(sys.stdin)[0]; print(f\\\"{d['user']}:{d['pass']}\\\")\")"
    exit 1
  fi
  curl -X POST "https://jewishcoach-api.scm.azurewebsites.net/api/zipdeploy?isAsync=true" \
    -u "$PUBLISH_PROFILE" -H "Content-Type: application/octet-stream" --data-binary @deploy.zip
  echo "✅ Zip uploaded (wait 2-5 min for app restart)"
fi

echo ""
echo "🔍 Check health: curl -s https://jewishcoach-api.azurewebsites.net/health | python3 -m json.tool"
