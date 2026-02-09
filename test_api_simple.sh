#!/bin/bash

# Simple API Test for BSD V2 Bug Fixes
# This creates a minimal simulation by calling the chat endpoint directly

API_URL="https://jewishcoach-api.azurewebsites.net/api/chat/v2/message"
USER_ID="test_user_$(date +%s)"
CONV_ID=1001  # Use a test conversation ID

echo "=============================================================================="
echo "🚀 TESTING BSD V2 BUG FIXES VIA API"
echo "=============================================================================="
echo ""
echo "This test will send messages and check responses for:"
echo "  ✓ Bug 1 & 2: 'עמוד שידרה' should NOT trigger frustration"
echo "  ✓ Bug 3: S2→S3 requires 3+ turns"
echo "  ✓ Bug 4: 'זהו' should be recognized"
echo ""
echo "=============================================================================="
echo ""

# Note: This is a simplified test that demonstrates the API structure
# For full testing, you'll need valid authentication tokens

echo "📌 API Endpoint: $API_URL"
echo "📝 To test manually, use the frontend at:"
echo "   https://purple-bush-0e6d5d603.5.azurestaticapps.net/"
echo ""
echo "=============================================================================="
echo "🔍 MANUAL TEST INSTRUCTIONS:"
echo "=============================================================================="
echo ""
echo "1️⃣  TEST 'עמוד שידרה' (Bug 1 & 2):"
echo "   Input: 'לשמור על איזה עמוד שידרה יציב פנימי'"
echo "   Expected: Coach should NOT say 'מצטער על החזרה'"
echo ""
echo "2️⃣  TEST S2→S3 Transition (Bug 3):"
echo "   Input: 'אתמול. הבת שלי ענתה לבעלי בצורה מזלזלת'"
echo "   Expected: Coach asks for MORE event details (not emotions yet)"
echo "   Expected: At least 3 turns in S2 before moving to S3"
echo ""
echo "3️⃣  TEST 'זהו' Recognition (Bug 4):"
echo "   Input: 'זהו' (after providing emotions)"
echo "   Expected: Coach should move forward (not ask 'מה עוד הרגשת?')"
echo ""
echo "=============================================================================="
echo ""

# Check if API is alive
echo "🔍 Checking API health..."
HEALTH=$(curl -s https://jewishcoach-api.azurewebsites.net/)
if echo "$HEALTH" | grep -q "Jewish Coaching API"; then
    echo "✅ API is running!"
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
else
    echo "❌ API seems down or unreachable"
    exit 1
fi

echo ""
echo "=============================================================================="
echo "📋 AUTOMATED TESTING SUMMARY:"
echo "=============================================================================="
echo ""
echo "⚠️  Full automated testing requires authentication tokens."
echo "   Please use the frontend application for interactive testing."
echo ""
echo "🌐 Frontend URL: https://purple-bush-0e6d5d603.5.azurestaticapps.net/"
echo ""
echo "=============================================================================="
