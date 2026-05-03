#!/usr/bin/env bash
# After DNS records in scripts/jewishcoacher_acs_dns_records.txt are live:
# - Re-run ACS verification
# - Wait until Domain + SPF + DKIM + DKIM2 show Verified
# - Register MailFrom local-part (default: ishai) and set EMAIL_SENDER on jewishcoach-api
#
# Requires: az CLI + communication extension, logged into the correct subscription.

set -euo pipefail

RG="${AZURE_RESOURCE_GROUP:-jewish-coach-rg}"
EMAIL_SVC="${ACS_EMAIL_SERVICE:-jewishcoach-email-svc}"
DOMAIN="${ACS_EMAIL_DOMAIN:-jewishcoacher.com}"
APP="${AZURE_WEBAPP_NAME:-jewishcoach-api}"
SENDER_LOCAL="${ACS_SENDER_LOCAL_PART:-ishai}"

poll_json() {
  az communication email domain show \
    --resource-group "$RG" \
    --email-service-name "$EMAIL_SVC" \
    --name "$DOMAIN" \
    -o json 2>/dev/null
}

echo "Re-initiating verification (Domain, SPF, DKIM, DKIM2)..."
for t in Domain SPF DKIM DKIM2; do
  az communication email domain initiate-verification \
    --resource-group "$RG" \
    --email-service-name "$EMAIL_SVC" \
    --domain-name "$DOMAIN" \
    --verification-type "$t" \
    -o none 2>/dev/null || true
done

echo "Polling verificationStates (Domain/SPF/DKIM/DKIM2 → Verified). Ctrl+C to stop."
all_verified() {
  python3 -c 'import json,sys
d=json.load(sys.stdin)
vs=d.get("verificationStates") or {}
for k in ("Domain","SPF","DKIM","DKIM2"):
    if (vs.get(k) or {}).get("status")!="Verified":
        sys.exit(1)
sys.exit(0)
'
}

for _ in $(seq 1 120); do
  raw="$(poll_json)"
  if [[ -n "$raw" ]] && echo "$raw" | all_verified; then
    echo "Domain authentication verified."
    echo "$raw" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin).get('verificationStates'), indent=2))"
    break
  fi
  echo "$raw" | python3 -c "import json,sys; d=json.load(sys.stdin); vs=d.get('verificationStates') or {}; print({k:(vs.get(k) or {}).get('status') for k in ('Domain','SPF','DKIM','DKIM2','DMARC')})" 2>/dev/null || true
  sleep 30
done

raw="$(poll_json)"
if ! echo "$raw" | all_verified; then
  echo "Not verified yet — confirm DNS at Hostinger matches scripts/jewishcoacher_acs_dns_records.txt then re-run this script."
  exit 1
fi

echo "Creating sender username: ${SENDER_LOCAL}@${DOMAIN}"
az communication email domain sender-username create \
  --resource-group "$RG" \
  --email-service-name "$EMAIL_SVC" \
  --domain-name "$DOMAIN" \
  --sender-username "$SENDER_LOCAL" \
  --username "$SENDER_LOCAL" \
  --display-name "Jewish Coach" \
  -o none

echo "Setting App Service EMAIL_SENDER..."
az webapp config appsettings set \
  --name "$APP" \
  --resource-group "$RG" \
  --settings "EMAIL_SENDER=${SENDER_LOCAL}@${DOMAIN}" \
  -o none

az webapp restart --name "$APP" --resource-group "$RG" -o none
echo "Done. MAIL FROM is ${SENDER_LOCAL}@${DOMAIN} on $APP"
