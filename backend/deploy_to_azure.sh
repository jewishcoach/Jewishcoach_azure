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
  # --enable-kudu-warmup false: avoid 503 when Kudu warm-up fails
  # --async true: avoid timeout on large zips
  # --restart true: ensure app picks up new code
  az webapp deploy \
    --resource-group jewish-coach-rg \
    --name jewishcoach-api \
    --src-path deploy.zip \
    --type zip \
    --enable-kudu-warmup false \
    --async true \
    --restart true
  echo "✅ Deployed via Azure CLI (async - wait 2-5 min for app restart)"
else
  echo "⚠️  Azure CLI not found. Using curl (need PUBLISH_PROFILE):"
  if [ -z "$PUBLISH_PROFILE" ]; then
    echo "Run: PUBLISH_PROFILE=\$(az webapp deployment list-publishing-profiles --name jewishcoach-api --resource-group jewish-coach-rg --query \"[?publishMethod=='MSDeploy'].{user:userName,pass:userPWD}\" -o json | python3 -c \"import sys, json; d=json.load(sys.stdin)[0]; print(f\\\"{d['user']}:{d['pass']}\\\")\")"
    exit 1
  fi
  curl -X POST \
    "https://jewishcoach-api.scm.azurewebsites.net/api/zipdeploy" \
    -u "$PUBLISH_PROFILE" \
    -H "Content-Type: application/octet-stream" \
    --data-binary @deploy.zip
  echo "✅ Deployed via curl (wait 2-5 min for app to restart)"
fi

echo ""
echo "🔍 Check health: curl -s https://jewishcoach-api.azurewebsites.net/health | python3 -m json.tool"
