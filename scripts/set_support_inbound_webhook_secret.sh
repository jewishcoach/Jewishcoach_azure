#!/usr/bin/env bash
# הגדרת SUPPORT_INBOUND_WEBHOOK_SECRET ב-Azure App Service (Make/Zapier → inbound-json).
#
# דורש: az login
#
# שימוש:
#   ./scripts/set_support_inbound_webhook_secret.sh
#   SUPPORT_INBOUND_WEBHOOK_SECRET="הסוד_שלי" ./scripts/set_support_inbound_webhook_secret.sh
#
# אופציונלי:
#   SUPPORT_INBOUND_MAILBOX=support@jewishcoacher.com (ברירת מחדל זהה)

set -euo pipefail

APP_NAME="${AZURE_WEBAPP_NAME:-jewishcoach-api}"
RG="${AZURE_RESOURCE_GROUP:-jewish-coach-rg}"

if ! command -v az >/dev/null 2>&1; then
  echo "❌Azure CLI (az) לא מותקן. התקן מ: https://learn.microsoft.com/cli/azure/install-azure-cli"
  exit 1
fi

if [ -z "${SUPPORT_INBOUND_WEBHOOK_SECRET:-}" ]; then
  SUPPORT_INBOUND_WEBHOOK_SECRET="$(openssl rand -hex 32)"
  echo "🔑 נוצר סוד אקראי (שמור אותו ל-Make בכותרת X-Support-Inbound-Secret)"
fi

MAILBOX="${SUPPORT_INBOUND_MAILBOX:-support@jewishcoacher.com}"

echo "מגדיר ב-Azure: $APP_NAME (resource group: $RG)..."
az webapp config appsettings set \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --settings \
  SUPPORT_INBOUND_WEBHOOK_SECRET="$SUPPORT_INBOUND_WEBHOOK_SECRET" \
  SUPPORT_INBOUND_MAILBOX="$MAILBOX" \
  -o none

echo "מפעיל מחדש את האפליקציה..."
az webapp restart --name "$APP_NAME" --resource-group "$RG" -o none

echo ""
echo "✅ בוצע."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "הדבק ב-Make (HTTP module → Headers):"
echo "  Name:  X-Support-Inbound-Secret"
echo "  Value: $SUPPORT_INBOUND_WEBHOOK_SECRET"
echo ""
echo "URL ל-POST JSON:"
echo "  https://api.jewishcoacher.com/api/internal/support-email/inbound-json"
echo "  (או: https://${APP_NAME}.azurewebsites.net/api/internal/support-email/inbound-json)"
echo ""
echo "Authentication ב-Make: None — לא Basic auth."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
