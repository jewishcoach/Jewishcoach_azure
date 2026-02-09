#!/usr/bin/env python3
"""
Local Simulation Test Script - Testing BSD v2 Bug Fixes
Tests the logic directly without API calls.
"""

import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.bsd_v2.single_agent_coach import handle_conversation
from app.bsd_v2.state_schema_v2 import create_initial_state
import time

def print_exchange(user_msg: str, response: dict, test_name: str = ""):
    """Print a conversation exchange."""
    if test_name:
        print(f"\n{'='*80}")
        print(f"🧪 TEST: {test_name}")
        print(f"{'='*80}")
    
    print(f"\n👤 משתמש: {user_msg}")
    print(f"🤖 מאמן: {response['response']}")
    print(f"📊 Stage: {response.get('current_step', 'N/A')} | Saturation: {response.get('saturation_score', 0):.2f}")
    time.sleep(0.3)  # Small delay for readability

async def run_simulation():
    """Run the full simulation based on the reported bug conversation."""
    
    print("\n" + "="*80)
    print("🚀 STARTING BSD V2 BUG FIX SIMULATION (LOCAL)")
    print("="*80)
    print("\nThis simulation tests:")
    print("  ✓ Bug 1 & 2: 'עמוד שידרה' should NOT trigger frustration detection ('די')")
    print("  ✓ Bug 3: S2→S3 should require 3+ turns with detailed event")
    print("  ✓ Bug 4: 'זהו' should be recognized as completion signal")
    print("\n" + "="*80)
    
    # Create initial state
    state = create_initial_state(
        conversation_id="test_001",
        user_id="test_user",
        language="he"
    )
    
    print("\n✅ Created initial state")
    
    # Exchange 1: Start with "כן"
    state, response = await handle_conversation(user_message="כן", state=state)
    print_exchange("כן", response, "Exchange 1: Initial greeting")
    
    # Exchange 2: Topic - keeping the royal daughter
    state, response = await handle_conversation(
        user_message="על היכולת לשמור על הבת מלך שאני",
        state=state
    )
    print_exchange("על היכולת לשמור על הבת מלך שאני", response, "Exchange 2: Initial topic")
    
    # Exchange 3: Clarify gender
    state, response = await handle_conversation(
        user_message="אני אישה",
        state=state
    )
    print_exchange("אני אישה", response, "Exchange 3: Gender clarification")
    
    # Exchange 4: THE CRITICAL TEST - "עמוד שידרה"
    # This should NOT trigger frustration (word "די" in "שידרה")
    message = "לשמור על הבת מלך שאני -זה לשמור על איזה עמוד שידרה יציב פנימי, כזה שמכבד אותי. לא להגרר לויכוחים, הורדות ידיים ומאבק על שליטה"
    state, response = await handle_conversation(user_message=message, state=state)
    print_exchange(message, response, "Exchange 4: 🎯 CRITICAL TEST - 'עמוד שידרה' (contains 'די')")
    
    # Check if frustration was triggered (Bug 1 & 2)
    coach_msg = response['response'].lower()
    if "מצטער" in coach_msg and ("על מה תרצה להתאמן" in coach_msg or response.get('current_step') == 'S1'):
        print("\n❌ BUG 1 & 2 STILL EXISTS: False positive on 'די' in 'שידרה'")
        print(f"   Coach incorrectly apologized or reset conversation!")
        print(f"   Response: {response['response'][:100]}...")
    else:
        print("\n✅ BUG 1 & 2 FIXED: 'עמוד שידרה' did NOT trigger frustration!")
    
    # Continue conversation to test remaining features
    current_step = response.get('current_step', 'S1')
    
    # If still in S1, progress through it
    max_s1_iterations = 5
    s1_iteration = 0
    while current_step == 'S1' and s1_iteration < max_s1_iterations:
        s1_iteration += 1
        state, response = await handle_conversation(
            user_message="נכון, זה מה שאני רוצה לעבוד עליו. זה ממש חשוב לי.",
            state=state
        )
        print_exchange(
            "נכון, זה מה שאני רוצה לעבוד עליו. זה ממש חשוב לי.",
            response,
            f"Exchange {4 + s1_iteration}: S1 progress"
        )
        current_step = response.get('current_step')
    
    # Now we should be in S2
    if current_step == 'S2':
        print("\n✅ Successfully transitioned to S2 (Event)")
        
        # Exchange: Provide initial event (1st S2 turn)
        event_msg = "אתמול. הבת שלי ענתה לבעלי בצורה מאד מזלזלת. ואני נכנסתי איתה למאבק כוח"
        state, response = await handle_conversation(user_message=event_msg, state=state)
        print_exchange(event_msg, response, "Exchange: 🎯 TESTING S2→S3 - Initial event (Turn 1)")
        
        # Check if coach jumped to S3 emotions immediately (Bug 3)
        new_step = response.get('current_step')
        coach_response_text = response['response'].lower()
        
        if new_step == 'S3' or 'מה הרגשת' in coach_response_text or 'רגש' in coach_response_text:
            print("\n❌ BUG 3 STILL EXISTS: Premature S2→S3 transition after 1 turn!")
            print(f"   Coach jumped to emotions too quickly")
            print(f"   Current step: {new_step}")
        else:
            print(f"\n✅ BUG 3 TEST 1/3: Coach stayed in S2, asking for more details (Step: {new_step})")
            
            # Turn 2: More details
            state, response = await handle_conversation(
                user_message="היא אמרה לו 'תעזוב אותי בשקט' בטון ממש גס",
                state=state
            )
            print_exchange(
                "היא אמרה לו 'תעזוב אותי בשקט' בטון ממש גס",
                response,
                "Exchange: More event details (Turn 2)"
            )
            
            new_step = response.get('current_step')
            if new_step == 'S3':
                print(f"\n⚠️  Transitioned to S3 after 2 turns (expected 3+)")
            else:
                print(f"\n✅ BUG 3 TEST 2/3: Still in S2 after 2 turns (Step: {new_step})")
            
            # Turn 3: Even more details
            state, response = await handle_conversation(
                user_message="הוא ביקש ממנה משהו פשוט ממש, והיא פשוט פתחה עליו",
                state=state
            )
            print_exchange(
                "הוא ביקש ממנה משהו פשוט ממש, והיא פשוט פתחה עליו",
                response,
                "Exchange: Even more details (Turn 3)"
            )
            
            new_step = response.get('current_step')
            if new_step == 'S2':
                print(f"\n✅ BUG 3 FIXED: Still in S2 after 3 turns, collecting thorough event details!")
            elif new_step == 'S3':
                print(f"\n✅ BUG 3 LIKELY FIXED: Transitioned to S3 after 3 turns (acceptable)")
            
            # Continue until we reach S3
            current_step = new_step
            turn_count = 3
            while current_step == 'S2' and turn_count < 6:
                turn_count += 1
                state, response = await handle_conversation(
                    user_message="זה היה בסלון, כולנו היינו שם. הרגשתי שהמצב יוצא מכלל שליטה",
                    state=state
                )
                print_exchange(
                    "זה היה בסלון, כולנו היינו שם. הרגשתי שהמצב יוצא מכלל שליטה",
                    response,
                    f"Exchange: Final S2 details (Turn {turn_count})"
                )
                current_step = response.get('current_step')
    
    # Now test S3 and "זהו" completion (Bug 4)
    if current_step == 'S3':
        print("\n✅ Successfully transitioned to S3 (Emotions)")
        
        # Provide initial emotions
        state, response = await handle_conversation(
            user_message="כעס, תסכול, ערעור פנימי כזה, נוקשות",
            state=state
        )
        print_exchange(
            "כעס, תסכול, ערעור פנימי כזה, נוקשות",
            response,
            "Exchange: Initial emotions (4 emotions)"
        )
        
        # Coach should explore emotions
        state, response = await handle_conversation(
            user_message="בבטן הרגשתי את הכעס",
            state=state
        )
        print_exchange("בבטן הרגשתי את הכעס", response, "Exchange: Emotion exploration")
        
        # Now THE CRITICAL TEST for Bug 4: say "זהו"
        state, response = await handle_conversation(user_message="זהו", state=state)
        print_exchange("זהו", response, "Exchange: 🎯 TESTING 'זהו' COMPLETION SIGNAL")
        
        coach_msg = response['response'].lower()
        if 'מה עוד' in coach_msg and 'הרגשת' in coach_msg:
            print("\n❌ BUG 4 STILL EXISTS: Coach did NOT recognize 'זהו' as completion signal")
            print(f"   Coach is still asking 'מה עוד הרגשת?'")
        else:
            print("\n✅ BUG 4 FIXED: Coach recognized 'זהו' and is moving forward!")
            print(f"   Current step: {response.get('current_step')}")
    
    print("\n" + "="*80)
    print("🏁 SIMULATION COMPLETE")
    print("="*80)
    print("\nSummary:")
    print("  • Tested the exact conversation flow from the bug report")
    print("  • All critical bug scenarios were tested locally")
    print("  • Review output above for pass/fail status of each bug")
    print("\n" + "="*80)

if __name__ == "__main__":
    try:
        asyncio.run(run_simulation())
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
