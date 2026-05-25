#!/usr/bin/env bash
#
# Jewish Coach — הפעלת PostgreSQL ב-Azure ליציבות ריבוי משתמשים
#
# לפני ההרצה:
#   1. התקן Azure CLI: https://learn.microsoft.com/cli/azure/install-azure-cli
#   2. התחבר:  az login --use-device-code
#   3. הגדר סיסמת מנהל Postgres (לא לשמור בריפו):
#        export AZURE_PG_ADMIN_PASSWORD='סיסמה-חזקה-לפחות-12-תווים'
#
# הרצה:
#        bash scripts/azure_enable_postgres_for_multiuser.sh
#
# משתני עקיפה (אופציונלי):
#   AZURE_RESOURCE_GROUP     ברירת מחדל: jewish-coach-rg
#   AZURE_WEBAPP_NAME        ברירת מחדל: jewishcoach-api
#   AZURE_PG_SERVER_NAME     ברירת מחדל: jewishcoach-pg
#   AZURE_PG_ADMIN_USER      ברירת מחדל: jcadmin
#   AZURE_PG_DATABASE        ברירת מחדל: jewishcoach
#   AZURE_PG_LOCATION        אזור יצירת Postgres (ברירת מחדל: כמו ה-Web App; אם האזור חסום — westus2 / westeurope)
#   SKIP_CONFIRM=1           דילוג על אישור אינטראקטיבי (אוטומציה בלבד)
#
set -euo pipefail

RG="${AZURE_RESOURCE_GROUP:-jewish-coach-rg}"
WEBAPP="${AZURE_WEBAPP_NAME:-jewishcoach-api}"
PG_NAME="${AZURE_PG_SERVER_NAME:-jewishcoach-pg}"
ADMIN_USER="${AZURE_PG_ADMIN_USER:-jcadmin}"
DB_NAME="${AZURE_PG_DATABASE:-jewishcoach}"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo " Jewish Coach — הגדרת PostgreSQL לריבוי משתמשים"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

if ! command -v az >/dev/null 2>&1; then
  echo "❌ חסר Azure CLI. התקנה: https://learn.microsoft.com/cli/azure/install-azure-cli"
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "❌ לא מחובר ל-Azure. הרץ:  az login --use-device-code"
  exit 1
fi

if [ -z "${AZURE_PG_ADMIN_PASSWORD:-}" ]; then
  echo "❌ חסר משתנה סביבה AZURE_PG_ADMIN_PASSWORD"
  echo "   דוגמה:  export AZURE_PG_ADMIN_PASSWORD='……'"
  exit 1
fi

if [ "${#AZURE_PG_ADMIN_PASSWORD}" -lt 12 ]; then
  echo "❌ סיסמת המנהל קצרה מדי (מומלץ לפחות 12 תווים)."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ נדרש python3 לקידוד סיסמה ולהגדרות האפליקציה."
  exit 1
fi

if [ "${SKIP_CONFIRM:-0}" != "1" ]; then
  echo "⚠️  הפעולה תיצור (אם חסר) שרת PostgreSQL בתשלום חודשי ב-Azure."
  echo "    השרת והמסד ישמשו את האפליקציה במקום קובץ SQLite."
  echo ""
  read -r -p "להמשיך? הקלד yes ואז Enter: " ans
  if [ "${ans}" != "yes" ]; then
    echo "בוטל."
    exit 0
  fi
fi

echo ""
echo "→ בודק קבוצת משאבים ו-Web App…"
az group show --name "$RG" >/dev/null
az webapp show --resource-group "$RG" --name "$WEBAPP" >/dev/null

LOCATION="$(az webapp show --resource-group "$RG" --name "$WEBAPP" --query location -o tsv)"
echo "   אזור Web App: $LOCATION"

PG_LOCATION="${AZURE_PG_LOCATION:-$LOCATION}"
if [ -n "${AZURE_PG_LOCATION:-}" ]; then
  echo "   אזור Postgres (AZURE_PG_LOCATION): $PG_LOCATION"
else
  echo "   אזור Postgres: $PG_LOCATION (ברירת מחדל — כמו Web App)"
fi

EXISTING_DB_URL="$(az webapp config appsettings list --resource-group "$RG" --name "$WEBAPP" \
  --query "[?name=='DATABASE_URL'].value | [0]" -o tsv 2>/dev/null || true)"
if [[ -n "$EXISTING_DB_URL" ]] && [[ "$EXISTING_DB_URL" == *"postgres"* ]]; then
  echo ""
  echo "ℹ️  DATABASE_URL כבר מצביע על PostgreSQL — לא יוצרים שרת חדש."
  echo "    אם צריך שרת נוסף, שנה AZURE_PG_SERVER_NAME או עדכן הגדרות ידנית בפורטל."
  exit 0
fi

if az postgres flexible-server show --resource-group "$RG" --name "$PG_NAME" >/dev/null 2>&1; then
  echo "→ שרת Postgres קיים: $PG_NAME"
else
  echo ""
  echo "→ יוצר שרת PostgreSQL Flexible Server (יכול לקחת כמה דקות)…"
  az postgres flexible-server create \
    --resource-group "$RG" \
    --name "$PG_NAME" \
    --location "$PG_LOCATION" \
    --admin-user "$ADMIN_USER" \
    --admin-password "$AZURE_PG_ADMIN_PASSWORD" \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --storage-size 32 \
    --version 16 \
    --public-access Enabled \
    --yes

fi

echo "→ ממתין שהשרת Postgres יהיה במצב Ready…"
for _attempt in $(seq 1 90); do
  STATE="$(az postgres flexible-server show --resource-group "$RG" --name "$PG_NAME" --query state -o tsv 2>/dev/null || true)"
  if [ "$STATE" = "Ready" ]; then
    echo "   השרת מוכן."
    break
  fi
  if [ "$_attempt" -eq 90 ]; then
    echo "❌ Timeout — השרת לא הגיע למצב Ready."
    exit 1
  fi
  sleep 20
done

echo ""
echo "→ מגדיר חוקי Firewall (גישה משירותי Azure + כתובות יציאה של ה-Web App)…"

if ! az postgres flexible-server firewall-rule show \
  --resource-group "$RG" \
  --name "$PG_NAME" \
  --rule-name AllowAzureServices >/dev/null 2>&1; then
  az postgres flexible-server firewall-rule create \
    --resource-group "$RG" \
    --name "$PG_NAME" \
    --rule-name AllowAzureServices \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0
fi

OUTBOUND="$(az webapp show --resource-group "$RG" --name "$WEBAPP" --query outboundIpAddresses -o tsv || true)"
IFS=',' read -ra IPS <<< "${OUTBOUND:-}"
for raw_ip in "${IPS[@]}"; do
  ip="${raw_ip// /}"
  [[ -z "$ip" ]] && continue
  rule_name="WebAppOut_${ip//./_}"
  if ! az postgres flexible-server firewall-rule show \
    --resource-group "$RG" \
    --name "$PG_NAME" \
    --rule-name "$rule_name" >/dev/null 2>&1; then
    az postgres flexible-server firewall-rule create \
      --resource-group "$RG" \
      --name "$PG_NAME" \
      --rule-name "$rule_name" \
      --start-ip-address "$ip" \
      --end-ip-address "$ip"
  fi
done

echo ""
_DB_LIST="$(az postgres flexible-server db list --resource-group "$RG" --server-name "$PG_NAME" --query "[].name" -o tsv 2>/dev/null || true)"
if echo "$_DB_LIST" | grep -qx "$DB_NAME"; then
  echo "→ מסד הנתונים כבר קיים: $DB_NAME"
else
  echo "→ יוצר מסד לוגי: $DB_NAME"
  az postgres flexible-server db create \
    --resource-group "$RG" \
    --server-name "$PG_NAME" \
    --database-name "$DB_NAME"
fi

FQDN="${PG_NAME}.postgres.database.azure.com"
ENC_PASS="$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$AZURE_PG_ADMIN_PASSWORD")"
DATABASE_URL="postgresql+psycopg2://${ADMIN_USER}:${ENC_PASS}@${FQDN}:5432/${DB_NAME}?sslmode=require"

SETTINGS_JSON="$(mktemp)"
trap 'rm -f "${SETTINGS_JSON}"' EXIT

export _JC_SETTINGS_PATH="$SETTINGS_JSON"
export _JC_DATABASE_URL="$DATABASE_URL"
python3 << 'PYCODE'
import json
import os

path = os.environ["_JC_SETTINGS_PATH"]
db_url = os.environ["_JC_DATABASE_URL"]
payload = [
    {"name": "DATABASE_URL", "value": db_url, "slotSetting": False},
    {"name": "GUNICORN_WORKERS", "value": "2", "slotSetting": False},
    {"name": "DB_POOL_SIZE", "value": "3", "slotSetting": False},
    {"name": "DB_MAX_OVERFLOW", "value": "5", "slotSetting": False},
]
with open(path, "w", encoding="utf-8") as f:
    json.dump(payload, f)
PYCODE

unset _JC_SETTINGS_PATH _JC_DATABASE_URL || true

echo ""
echo "→ מעדכן Application Settings ב-$WEBAPP …"
az webapp config appsettings set \
  --resource-group "$RG" \
  --name "$WEBAPP" \
  --settings "@${SETTINGS_JSON}"

echo ""
echo "→ מאתחל את ה-Web App…"
az webapp restart --resource-group "$RG" --name "$WEBAPP"

DEFAULT_HOST="$(az webapp show --resource-group "$RG" --name "$WEBAPP" --query defaultHostName -o tsv)"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo " ✅ סיום."
echo ""
echo " PostgreSQL:   $FQDN"
echo " מסד לוגי:    $DB_NAME"
echo " בדיקת בריאות: https://${DEFAULT_HOST}/health"
echo ""
echo " חשוב:"
echo "   • לראשונה האפליקציה תיצור טבלאות ריקות — היסטוריית שיחות ישנה ב-SQLite"
echo "     לא עוברת אוטומטית. להעברה ידנית ראה:"
echo "       backend/docs/POSTGRESQL_AZURE_RUNBOOK.md"
echo "       backend/scripts/sqlite_to_postgres.py"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
