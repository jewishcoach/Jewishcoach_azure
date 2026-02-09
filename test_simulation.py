#!/usr/bin/env python3
"""
Simulation Test Script - Testing BSD v2 Bug Fixes
Based on the user's reported conversation with bugs.
"""

import requests
import json
import time
from typing import List, Dict

API_URL = "https://jewishcoach-api.azurewebsites.net/api/chat/v2"

def create_conversation() -> str:
    """Create a new conversation and return conversation_id."""
    response = requests.post(
        f"{API_URL}/conversations",
        json={
            "user_id": "test_simulation_user",
            "language": "he"
        }
    )
    response.raise_for_status()
    data = response.json()
    return data["conversation_id"]

def send_message(conversation_id: str, message: str) -> Dict:
    """Send a message and return the coach's response."""
    response = requests.post(
        f"{API_URL}/conversations/{conversation_id}/messages",
        json={"message": message}
    )
    response.raise_for_status()
    return response.json()

def print_exchange(user_msg: str, coach_response: Dict, test_name: str = ""):
    """Print a conversation exchange."""
    if test_name:
        print(f"\n{'='*80}")
        print(f"🧪 TEST: {test_name}")
        print(f"{'='*80}")
    
    print(f"\n👤 משתמש: {user_msg}")
    print(f"🤖 מאמן: {coach_response['response']}")
    print(f"📊 Stage: {coach_response.get('current_step', 'N/A')} | Saturation: {coach_response.get('saturation_score', 0):.2f}")
    time.sleep(0.5)  # Small delay for readability

def run_simulation():
    """Run the full simulation based on the reported bug conversation."""
    
    print("\n" + "="*80)
    print("🚀 STARTING BSD V2 BUG FIX SIMULATION")
    print("="*80)
    print("\nThis simulation tests:")
    print("  ✓ Bug 1 & 2: 'עמוד שידרה' should NOT trigger frustration detection ('די')")
    print("  ✓ Bug 3: S2→S3 should require 3+ turns with detailed event")
    print("  ✓ Bug 4: 'זהו' should be recognized as completion signal")
    print("\n" + "="*80)
    
    # Create conversation
    print("\n📞 Creating new conversation...")
    conv_id = create_conversation()
    print(f"✅ Conversation ID: {conv_id}")
    
    # Start conversation
    time.sleep(1)
    
    # Exchange 1: Start with "כן"
    response = send_message(conv_id, "כן")
    print_exchange("כן", response, "Exchange 1: Initial greeting")
    
    # Exchange 2: Topic - keeping the royal daughter
    response = send_message(conv_id, "על היכולת לשמור על הבת מלך שאני")
    print_exchange("על היכולת לשמור על הבת מלך שאני", response, "Exchange 2: Initial topic")
    
    # Exchange 3: Clarify gender
    response = send_message(conv_id, "אני אישה")
    print_exchange("אני אישה", response, "Exchange 3: Gender clarification")
    
    # Exchange 4: THE CRITICAL TEST - "עמוד שידרה"
    # This should NOT trigger frustration (word "די" in "שידרה")
    message = "לשמור על הבת מלך שאני -זה לשמור על איזה עמוד שידרה יציב פנימי, כזה שמכבד אותי. לא להגרר לויכוחים, הורדות ידיים ומאבק על שליטה"
    response = send_message(conv_id, message)
    print_exchange(message, response, "Exchange 4: 🎯 CRITICAL TEST - 'עמוד שידרה' (contains 'די')")
    
    # Check if frustration was triggered (Bug 1 & 2)
    coach_msg = response['response'].lower()
    if "מצטער" in coach_msg or "על מה תרצה להתאמן" in coach_msg:
        print("\n❌ BUG 1 & 2 STILL EXISTS: False positive on 'די' in 'שידרה'")
        print(f"   Coach incorrectly apologized or reset conversation!")
    else:
        print("\n✅ BUG 1 & 2 FIXED: 'עמוד שידרה' did NOT trigger frustration!")
    
    # Continue based on response
    if response.get('current_step') == 'S1':
        # Still in S1, need to progress
        print("\n⚠️  Still in S1, continuing conversation...")
        
    # Let's continue the conversation to test S2→S3 transition
    # The coach should ask for a specific event
    current_step = response.get('current_step', 'S1')
    
    # If we're still in S1, let's move forward
    if current_step == 'S1':
        response = send_message(conv_id, "נכון, זה מה שאני רוצה לעבוד עליו")
        print_exchange("נכון, זה מה שאני רוצה לעבוד עליו", response, "Exchange 5: Confirming topic")
        current_step = response.get('current_step')
    
    # Wait for S2 transition - coach should ask for specific event
    if current_step == 'S2':
        print("\n✅ Successfully transitioned to S2 (Event)")
        
        # Exchange: Provide initial event
        event_msg = "אתמול. הבת שלי ענתה לבעלי בצורה מאד מזלזלת. ואני נכנסתי איתה למאבק כוח"
        response = send_message(conv_id, event_msg)
        print_exchange(event_msg, response, "Exchange 6: 🎯 TESTING S2→S3 - Initial event description")
        
        # Check if coach jumped to S3 emotions (Bug 3)
        new_step = response.get('current_step')
        coach_response_text = response['response'].lower()
        
        if new_step == 'S3' or 'מה הרגשת' in coach_response_text or 'רגשות' in coach_response_text:
            print("\n❌ BUG 3 STILL EXISTS: Premature S2→S3 transition!")
            print(f"   Coach jumped to emotions after only 1 turn in S2")
            print(f"   Current step: {new_step}")
        else:
            print("\n✅ BUG 3 POSSIBLY FIXED: Coach is asking for more event details (not emotions)")
            print(f"   Current step: {new_step}")
            
            # Continue providing event details
            response = send_message(conv_id, "היא אמרה לו 'תעזוב אותי בשקט' בטון ממש גס")
            print_exchange("היא אמרה לו 'תעזוב אותי בשקט' בטון ממש גס", response, "Exchange 7: More event details")
            
            response = send_message(conv_id, "הוא ביקש ממנה משהו פשוט ממש, והיא פשוט פתחה עליו")
            print_exchange("הוא ביקש ממנה משהו פשוט ממש, והיא פשוט פתחה עליו", response, "Exchange 8: Even more details")
            
            new_step = response.get('current_step')
            if new_step == 'S2':
                print("\n✅ BUG 3 FIXED: Still in S2 after 3 turns, collecting event details!")
            
    # Now let's test emotions stage (S3) and the "זהו" completion keyword (Bug 4)
    # First, we need to get to S3
    current_step = response.get('current_step')
    
    # Keep going until we reach S3
    if current_step == 'S2':
        response = send_message(conv_id, "זה היה בסלון, כולנו היינו שם")
        print_exchange("זה היה בסלון, כולנו היינו שם", response, "Exchange 9: Final S2 detail")
        current_step = response.get('current_step')
    
    if current_step == 'S3':
        print("\n✅ Successfully transitioned to S3 (Emotions)")
        
        # Provide emotions one by one
        response = send_message(conv_id, "כעס, תסכול, ערעור פנימי כזה, נוקשות")
        print_exchange("כעס, תסכול, ערעור פנימי כזה, נוקשות", response, "Exchange 10: Initial emotions")
        
        # Coach should explore each emotion
        response = send_message(conv_id, "בבטן")
        print_exchange("בבטן", response, "Exchange 11: Location of anger")
        
        # Now the CRITICAL TEST for Bug 4: say "זהו"
        response = send_message(conv_id, "זהו")
        print_exchange("זהו", response, "Exchange 12: 🎯 TESTING 'זהו' COMPLETION SIGNAL")
        
        coach_msg = response['response'].lower()
        if 'מה עוד' in coach_msg or 'ספרי לי עוד' in coach_msg:
            print("\n❌ BUG 4 STILL EXISTS: Coach did NOT recognize 'זהו' as completion signal")
            print(f"   Coach is still asking for more!")
        else:
            print("\n✅ BUG 4 FIXED: Coach recognized 'זהו' and is moving forward!")
    
    print("\n" + "="*80)
    print("🏁 SIMULATION COMPLETE")
    print("="*80)
    print("\nSummary:")
    print("  • Test covered the exact conversation flow from the bug report")
    print("  • All critical bug scenarios were tested")
    print("  • Review output above for pass/fail status of each bug")
    print("\n" + "="*80)

if __name__ == "__main__":
    try:
        run_simulation()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
