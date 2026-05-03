#!/bin/bash
# הגדרת משתני מייל וסודות cron ב-Azure App Service (תזכורות + אונבורדינג).
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

# סוד זהה ברירת מחדל לשתי הקריאות המתוזמנות (ניתן לדרוס עם ONBOARDING_EMAIL_CRON_SECRET)
ONBOARDING_EMAIL_CRON_SECRET="${ONBOARDING_EMAIL_CRON_SECRET:-$REMINDER_CRON_SECRET}"

PUBLIC_APP_URL="${PUBLIC_APP_URL:-https://jewishcoacher.com}"

echo "מגדיר ב-Azure ($APP_NAME)..."
az webapp config appsettings set \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --settings \
    EMAIL_CONNECTION_STRING="$EMAIL_CONNECTION_STRING" \
    REMINDER_CRON_SECRET="$REMINDER_CRON_SECRET" \
    ONBOARDING_EMAIL_CRON_SECRET="$ONBOARDING_EMAIL_CRON_SECRET" \
    PUBLIC_APP_URL="$PUBLIC_APP_URL" \
  -o none

echo "✅ הוגדר. הפעל מחדש: az webapp restart --name $APP_NAME --resource-group $RG"
echo "REMINDER_CRON_SECRET (Logic App תזכורות): $REMINDER_CRON_SECRET"
echo "ONBOARDING_EMAIL_CRON_SECRET (GitHub Actions / cron אונבורדינג): $ONBOARDING_EMAIL_CRON_SECRET"
echo "הוסף ב-GitHub Secrets אותו ערך כמו ONBOARDING_EMAIL_CRON_SECRET + ONBOARDING_EMAIL_CRON_POST_URL (ראה onboarding-email-dispatch.yml)"
