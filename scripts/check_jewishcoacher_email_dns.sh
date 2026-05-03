#!/usr/bin/env bash
# Detect flaky apex TXT (SPF / Azure verification) across repeated Google DNS queries.
# If this prints INCONSISTENT, Azure may report MultipleSPFRecordsFound or random send failures.
#
# Correct fix: Hostinger → DNS zone — exactly ONE TXT @ starting with v=spf1 (merged line).
# If still flaky after edits: lower TTL on TXT @ to 300 temporarily; wait propagation;
# contact Hostinger support if authoritative servers disagree.

set -euo pipefail
DOMAIN="${1:-jewishcoacher.com}"
MERGED='v=spf1 include:_spf.mail.hostinger.com include:spf.protection.outlook.com ~all'
VER_PREFIX='ms-domain-verification='

echo "Sampling TXT@${DOMAIN} via Google DNS (15 tries, ~8s)..."
declare -A SEEN
for i in $(seq 1 15); do
  RAW=$(curl -sS "https://dns.google/resolve?name=${DOMAIN}&type=TXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('|'.join(sorted(a.get('data','') for a in d.get('Answer',[]) if a.get('type')==16)))") || RAW='ERROR'
  SEEN["$RAW"]=1
  SPFC=$(echo "$RAW" | tr '|' '\n' | grep -c '^v=spf1' || true)
  VER=$(echo "$RAW" | tr '|' '\n' | grep -c "^${VER_PREFIX}" || true)
  printf '%2d  SPF_TXT_lines=%s  has_verification=%s\n' "$i" "$SPFC" "$VER"
  sleep 0.55
done

echo ""
echo "Unique TXT bundles seen: ${#SEEN[@]}"
if [ "${#SEEN[@]}" -gt 1 ]; then
  echo "INCONSISTENT — authoritative DNS or resolver caching is not stable."
  echo "Canonical SPF must always be exactly:"
  echo "  ${MERGED}"
  exit 1
fi

# Single snapshot validation
ONE=$(printf '%s\n' "${!SEEN[@]}")
SPFC=$(echo "$ONE" | tr '|' '\n' | grep -c '^v=spf1' || true)
HAS_MERGED=$(echo "$ONE" | tr '|' '\n' | grep -Fx "$MERGED" >/dev/null && echo yes || echo no)

if [ "$SPFC" != "1" ] || [ "$HAS_MERGED" != "yes" ]; then
  echo "FAILED — expected exactly one merged SPF line plus verification TXT."
  echo "Bundle: ${ONE//|/ ; }"
  exit 1
fi

echo "OK — stable merged SPF + verification observed on all samples."
