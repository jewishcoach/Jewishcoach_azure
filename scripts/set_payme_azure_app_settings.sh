#!/usr/bin/env bash
# Set PayMe-related Application Settings on Azure Web App (after `az login` — device flow OK).
#
# Secrets MUST NOT be committed. Provide via environment variables when invoking:
#
#   export PAYME_API_KEY='YOUR_PAYME_KEY'
#   export PAYME_PAYMENTS_API_BASE='https://BASE_FROM_PAYME_DOCS'
#   # optional:
#   # export PAYME_WEBHOOK_SECRET='…'
#   bash scripts/set_payme_azure_app_settings.sh
#
# Overrides:
#   AZURE_WEBAPP_NAME=jewishcoach-api (default)
#   AZURE_RESOURCE_GROUP=jewish-coach-rg (default)
#
set -euo pipefail

APP_NAME="${AZURE_WEBAPP_NAME:-jewishcoach-api}"
RG="${AZURE_RESOURCE_GROUP:-jewish-coach-rg}"

if ! command -v az >/dev/null 2>&1; then
  echo "❌ Azure CLI (az) not installed. https://learn.microsoft.com/cli/azure/install-azure-cli"
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "❌ Not logged in. Run:  az login --use-device-code"
  exit 1
fi

if [ -z "${PAYME_API_KEY:-}" ]; then
  echo "❌ Missing PAYME_API_KEY (export it in this shell; do not commit)."
  exit 1
fi

if [ -z "${PAYME_PAYMENTS_API_BASE:-}" ]; then
  echo "❌ Missing PAYME_PAYMENTS_API_BASE."
  echo "   Example bases: Staging https://sandbox.payme.io/api  Production https://live.payme.io/api"
  echo "   Docs: https://docs.payme.io/docs/payments/v4n3lbk5v9qpj-sandbox-and-production-ur-ls"
  exit 1
fi

echo "Setting app settings on $APP_NAME (resource group: $RG)..."

SETTINGS=(
  "PAYME_API_KEY=$PAYME_API_KEY"
  "PAYME_PAYMENTS_API_BASE=${PAYME_PAYMENTS_API_BASE%/}"
)

if [ -n "${PAYME_WEBHOOK_SECRET:-}" ]; then
  SETTINGS+=("PAYME_WEBHOOK_SECRET=$PAYME_WEBHOOK_SECRET")
fi

# az accepts multiple --settings KEY=value pairs
az webapp config appsettings set \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --settings "${SETTINGS[@]}" \
  -o none

echo "Restarting web app..."
az webapp restart --name "$APP_NAME" --resource-group "$RG" -o none

echo ""
echo "✅ PayMe env vars applied on Azure."
echo "Verify after deploy (with user JWT): GET https://${APP_NAME}.azurewebsites.net/api/billing/payme/status"
