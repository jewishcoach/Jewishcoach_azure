#!/usr/bin/env bash
# Compare ACS Email verificationRecords vs live apex TXT (Google DNS JSON API).
# Run after editing SPF at Hostinger; then: bash scripts/acs_finalize_jewishcoacher_email.sh

set -euo pipefail

RG="${AZURE_RESOURCE_GROUP:-jewish-coach-rg}"
EMAIL_SVC="${ACS_EMAIL_SERVICE:-jewishcoach-email-svc}"
DOMAIN="${ACS_EMAIL_DOMAIN:-jewishcoacher.com}"

echo "Azure ACS expected values for domain '${DOMAIN}' (email service '${EMAIL_SVC}'):"
az communication email domain show \
  --resource-group "$RG" \
  --email-service-name "$EMAIL_SVC" \
  --domain-name "$DOMAIN" \
  --query "verificationRecords" \
  -o json 2>/dev/null | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin), indent=2, ensure_ascii=False))"

echo ""
echo "Live TXT@${DOMAIN} (resolver: dns.google):"
python3 << PY
import json, urllib.request
req = urllib.request.Request(
    "https://dns.google/resolve?name=${DOMAIN}&type=TXT",
    headers={"Accept": "application/dns-json"},
)
with urllib.request.urlopen(req, timeout=20) as r:
    d = json.loads(r.read().decode())
for a in d.get("Answer", []):
    if a.get("type") == 16:
        print(" ", a.get("data"))
PY

echo ""
echo "ACS verificationStates:"
az communication email domain show \
  --resource-group "$RG" \
  --email-service-name "$EMAIL_SVC" \
  --domain-name "$DOMAIN" \
  --query "verificationStates" \
  -o json
