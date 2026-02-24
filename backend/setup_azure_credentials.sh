#!/bin/bash
# Run this once to create AZURE_CREDENTIALS for GitHub Actions (fixes 409 deploy)
# Prerequisites: az CLI installed, logged in (az login)
#
# 1. Get your subscription ID:
#    az account show --query id -o tsv
#
# 2. Run (replace SUB_ID with your subscription ID):
#    az ad sp create-for-rbac --name "github-jewishcoach-deploy" \
#      --role contributor \
#      --scopes /subscriptions/SUB_ID/resourceGroups/jewish-coach-rg \
#      --sdk-auth
#
# 3. Copy the JSON output
# 4. GitHub → Settings → Secrets → Actions → New repository secret
#    Name: AZURE_CREDENTIALS
#    Value: (paste the JSON)

SUB_ID="${1:-$(az account show --query id -o tsv 2>/dev/null)}"
if [ -z "$SUB_ID" ]; then
  echo "Usage: $0 [subscription-id]"
  echo "Or: az login first, then $0"
  exit 1
fi
echo "Creating service principal for subscription $SUB_ID..."
az ad sp create-for-rbac --name "github-jewishcoach-deploy" \
  --role contributor \
  --scopes "/subscriptions/$SUB_ID/resourceGroups/jewish-coach-rg" \
  --sdk-auth
