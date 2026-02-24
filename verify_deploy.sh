#!/bin/bash
# Verify Azure backend has the new Azure-optimized prompts
API="https://jewishcoach-api.azurewebsites.net"

echo "🔍 Checking $API ..."
echo ""

# Root
echo "1. Root:"
curl -s --max-time 15 "$API/" | python3 -m json.tool 2>/dev/null || echo "   (timeout or error)"
echo ""

# Version (includes azure_optimized_prompts check)
echo "2. /api/version (deploy fingerprint):"
OUT=$(curl -s --max-time 15 "$API/api/version" 2>/dev/null)
if [ -n "$OUT" ]; then
  echo "$OUT" | python3 -m json.tool 2>/dev/null || echo "$OUT"
  if echo "$OUT" | grep -q '"azure_optimized_prompts": true'; then
    echo ""
    echo "✅ הקוד החדש מעודכן (Azure-optimized prompts)"
  elif echo "$OUT" | grep -q '"azure_optimized_prompts"'; then
    echo ""
    echo "⚠️  azure_optimized_prompts=false - ייתכן שעדיין גרסה ישנה"
  fi
else
  echo "   (timeout - ייתכן cold start)"
fi
echo ""

# Health
echo "3. /health:"
curl -s --max-time 15 "$API/health" | python3 -m json.tool 2>/dev/null | head -20 || echo "   (timeout or error)"
