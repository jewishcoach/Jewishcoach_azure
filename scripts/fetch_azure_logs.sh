#!/bin/bash
# Fetch Azure Web App logs via Kudu VFS API
# Usage: ./scripts/fetch_azure_logs.sh [grep_pattern] [log_filename]
# Example: ./scripts/fetch_azure_logs.sh "BSD|Safety"
# Example: ./scripts/fetch_azure_logs.sh "BSD" 2026_02_24_lw0sdlwk0008YP_default_docker.log

set -e
APP_NAME="${AZURE_WEBAPP_NAME:-jewishcoach-api}"
RG="${AZURE_RESOURCE_GROUP:-jewish-coach-rg}"
FILTER="${1:-BSD}"
SPECIFIC_LOG="${2:-}"

echo "Getting credentials..."
CREDS=$(az webapp deployment list-publishing-profiles \
  --name "$APP_NAME" --resource-group "$RG" \
  --query "[?publishMethod=='MSDeploy'].{user:userName,pass:userPWD}" -o json 2>/dev/null | \
  python3 -c "import sys, json; d=json.load(sys.stdin)[0]; print(f\"{d['user']}:{d['pass']}\")" 2>/dev/null)

if [ -z "$CREDS" ]; then
  echo "Error: Could not get credentials. Run 'az login' first."
  exit 1
fi

if [ -n "$SPECIFIC_LOG" ]; then
  LATEST="$SPECIFIC_LOG"
else
  echo "Listing log files..."
  # Get the most recent default_docker.log by mtime (application logs)
  LATEST=$(curl -s -u "$CREDS" "https://${APP_NAME}.scm.azurewebsites.net/api/vfs/LogFiles/" | \
    python3 -c "
import sys, json
items = json.load(sys.stdin)
logs = [x for x in items if 'default_docker' in x.get('name','') and x.get('mime')=='text/plain']
logs.sort(key=lambda x: x.get('mtime',''), reverse=True)
print(logs[0]['name'] if logs else '')
"
)
fi
echo "Fetching: $LATEST"
curl -s -u "$CREDS" "https://${APP_NAME}.scm.azurewebsites.net/api/vfs/LogFiles/${LATEST}" | grep -E "$FILTER" | tail -150
