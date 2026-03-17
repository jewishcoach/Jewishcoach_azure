#!/bin/bash
# הגדרת משתני תזכורות במייל ב-Azure App Service
# שימוש: EMAIL_CONNECTION_STRING="..." REMINDER_CRON_SECRET="..." ./scripts/set_azure_email_settings.sh
# או: ./scripts/set_azure_email_settings.sh  # יבקש את הערכים

set -e
APP_NAME="${AZURE_WEBAPP_NAME:-jewishcoach-api}"
RG="${AZURE_RESOURCE_GROUP:-jewish-coach-rg}"

if [ -z "$EMAIL_CONNECTION_STRING" ]; then
  echo "הזן EMAIL_CONNECTION_STRING (מ-Azure Communication Services → Keys):"
  read -r EMAIL_CONNECTION_STRING
fi

if [ -z "$REMINDER_CRON_SECRET" ]; then
  echo "הזן REMINDER_CRON_SECRET (או Enter ליצירת אקראי):"
  read -r REMINDER_CRON_SECRET
  [ -z "$REMINDER_CRON_SECRET" ] && REMINDER_CRON_SECRET=$(openssl rand -hex 24)
fi

echo "מגדיר ב-Azure ($APP_NAME)..."
az webapp config appsettings set \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --settings \
    EMAIL_CONNECTION_STRING="$EMAIL_CONNECTION_STRING" \
    REMINDER_CRON_SECRET="$REMINDER_CRON_SECRET" \
  -o none

echo "✅ הוגדר. הפעל מחדש: az webapp restart --name $APP_NAME --resource-group $RG"
echo "REMINDER_CRON_SECRET לשימוש ב-Logic App: $REMINDER_CRON_SECRET"
