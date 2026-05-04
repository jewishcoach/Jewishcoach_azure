#!/usr/bin/env bash
# Bind api.<your-domain> to Azure App Service and provision a free App Service Managed Certificate.
# Fixes browser ERR_SSL_PROTOCOL_ERROR when DNS points at the app but TLS was never issued/bound.
#
# Prerequisites:
#   - Azure CLI logged in: az login
#   - DNS at your registrar: CNAME api -> <webapp>.azurewebsites.net (no conflicting A/AAAA on api)
#
# Usage:
#   RG=jewish-coach-rg WEBAPP=jewishcoach-api HOST=api.jewishcoacher.com bash scripts/bind_app_service_api_hostname_tls.sh
# Non-interactive:
#   SKIP_CONFIRM=1 bash scripts/bind_app_service_api_hostname_tls.sh

set -euo pipefail

RG="${RG:-jewish-coach-rg}"
WEBAPP="${WEBAPP:-jewishcoach-api}"
HOST="${HOST:-api.jewishcoacher.com}"
SKIP_CONFIRM="${SKIP_CONFIRM:-}"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

command -v az >/dev/null || die "Azure CLI (az) not found."

echo "=== App Service custom hostname + Managed Certificate ==="
echo "Resource group: $RG"
echo "Web app:        $WEBAPP"
echo "Hostname:       $HOST"
echo ""
echo "DNS must resolve $HOST to Azure before Managed Certificate can validate (HTTP challenge)."
echo "  Recommended record:"
echo "    Type: CNAME"
echo "    Host: api  (or api.jewishcoacher.com — depends on DNS UI)"
echo "    Target: ${WEBAPP}.azurewebsites.net"
echo ""

if [[ "$SKIP_CONFIRM" != "1" ]]; then
  read -r -p "Continue? [y/N] " ans || true
  case "${ans,,}" in
    y|yes) ;;
    *) echo "Aborted."; exit 1 ;;
  esac
fi

echo ""
echo ">>> Adding hostname binding (idempotent if already present)..."
set +e
add_out="$(az webapp config hostname add \
  --resource-group "$RG" \
  --webapp-name "$WEBAPP" \
  --hostname "$HOST" 2>&1)"
add_rc=$?
set -e
if [[ $add_rc -ne 0 ]]; then
  if echo "$add_out" | grep -qiE 'already|exists|duplicat|conflict|taken'; then
    echo "Hostname likely already bound — continuing."
  else
    echo "$add_out" >&2
    die "hostname add failed (fix DNS / permissions / typos)."
  fi
else
  echo "$add_out"
fi

echo ""
echo ">>> Creating Managed Certificate (preview API; may take a minute)..."
az webapp config ssl create \
  --resource-group "$RG" \
  --name "$WEBAPP" \
  --hostname "$HOST"

echo ""
echo ">>> Listing certs in RG (thumbprint for manual bind if needed)..."
az webapp config ssl list --resource-group "$RG" -o table || true

echo ""
echo ">>> Verifying HTTPS (SNI)..."
if command -v curl >/dev/null; then
  curl -fsSI "https://${HOST}/health" | head -n 5 && echo "OK: HTTPS responds." || {
    echo "WARN: curl failed — wait 5–15 minutes for cert propagation, then retry:"
    echo "  curl -vI https://${HOST}/health"
  }
else
  echo "(install curl to auto-verify)"
fi

echo ""
echo "Done. Frontend should use https://${HOST}/api (see GitHub secret VITE_API_URL if you bake the URL at build time)."
