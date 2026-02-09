#!/usr/bin/env python3
"""
Local simulation - runs BSD v2 code directly (no API)
Tests the new fixes by running conversation logic locally
"""

import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.bsd_v2.single_agent_coach import handle_conversation
from app.bsd_v2.state_schema_v2 import create_initial_state, add_message

class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_stage_info(state):
    """Print current stage info"""
    step = state.get("current_step", "?")
    sat = state.get("saturation_score", 0)
    print(f"{Colors.YELLOW}[שלב {step}, רוויה {sat:.2f}]{Colors.END}")

async def simulate_conversation(messages):
    """
    Simulate a conversation with given messages
    
    Args:
        messages: List of user messages to send
    
    Returns:
        state after all messages
    """
    # Create initial state
    state = create_initial_state(
        conversation_id="test_123",
        user_id="test_user",
        language="he"
    )
    
    print(f"\n{Colors.BOLD}🚀 מתחיל סימולציה...{Colors.END}\n")
    
    for i, user_msg in enumerate(messages, 1):
        print(f"\n{Colors.BOLD}{'─'*80}{Colors.END}")
        print(f"{Colors.BLUE}👤 משתמש ({i}/{len(messages)}):{Colors.END} {user_msg}")
        
        # Add user message to state
        state = add_message(state, "user", user_msg)
        
        # Get coach response
        try:
            coach_response, state = await handle_conversation(
                user_message=user_msg,
                state=state,
                language="he"
            )
            
            current_step = state.get("current_step", "?")
            print(f"{Colors.GREEN}🤖 מאמן:{Colors.END} {coach_response}")
            print_stage_info(state)
            
        except Exception as e:
            print(f"{Colors.RED}❌ שגיאה: {e}{Colors.END}")
            import traceback
            traceback.print_exc()
            break
    
    return state

async def test_s2_to_s4_blocking():
    """
    Test 1: Verify S2→S4 is blocked (must go through S3)
    """
    print(f"\n{Colors.BOLD}{'='*80}")
    print(f"🧪 TEST 1: חסימת S2→S4 (חובה לעבור דרך S3)")
    print(f"{'='*80}{Colors.END}")
    
    messages = [
        "כן",  # S0
        "על הקשר שלי עם אחותי",  # S1
        "על היכולת להיות כנה וחמה אבל גם שומרת על גבולות",  # S1
        "היום אני נותנת הרבה ומרגישה שהיא לא מכבדת את הבית שלי",  # S1
        "הייתי רוצה שתהיה יותר רגישה לסגנון החיים שלי",  # S1
        "8",  # S1 → S2
        "אחותי ישבה אצלי כל השבת וחסמה את כל הבית עם הלימודים שלה למבחן",  # S2
    ]
    
    state = await simulate_conversation(messages)
    
    # Check: should be in S2 or S3, NOT S4
    current_step = state.get("current_step", "")
    print(f"\n{Colors.BOLD}🔍 תוצאות בדיקה:{Colors.END}")
    
    if current_step in ["S2", "S3"]:
        print(f"   {Colors.GREEN}✅ נכון: נמצא בשלב {current_step}{Colors.END}")
    elif current_step == "S4":
        print(f"   {Colors.RED}❌ שגוי: קפץ ל-S4 בלי לעבור דרך S3!{Colors.END}")
    else:
        print(f"   {Colors.YELLOW}⚠️  שלב לא צפוי: {current_step}{Colors.END}")
    
    # Continue to see transition
    print(f"\n{Colors.YELLOW}📝 ממשיך כדי לראות מעבר...{Colors.END}")
    
    more_messages = [
        "זה גרם לי לשים בצד את הרצונות שלי",  # S2
        "חשבתי שהיא מגזימה בהשתלטות",  # S2 or try to jump to S4?
    ]
    
    for msg in more_messages:
        state = add_message(state, "user", msg)
        coach_response, state = await handle_conversation(
            user_message=msg,
            state=state,
            language="he"
        )
        print(f"\n{Colors.BLUE}👤:{Colors.END} {msg}")
        print(f"{Colors.GREEN}🤖:{Colors.END} {coach_response}")
        print_stage_info(state)
    
    # Final check
    final_step = state.get("current_step", "")
    print(f"\n{Colors.BOLD}🎯 בדיקה סופית:{Colors.END}")
    
    if final_step == "S3":
        print(f"   {Colors.GREEN}✅ מושלם! עבר ל-S3 (רגשות) כמו שצריך{Colors.END}")
    elif final_step == "S4":
        print(f"   {Colors.RED}❌ באג! קפץ ל-S4 בלי רגשות{Colors.END}")
    else:
        print(f"   {Colors.YELLOW}⚠️  שלב: {final_step}{Colors.END}")
    
    return state

async def test_s2_questions():
    """
    Test 2: Verify S2 asks generic questions first
    """
    print(f"\n{Colors.BOLD}{'='*80}")
    print(f"🧪 TEST 2: שאלות גנריות ב-S2")
    print(f"{'='*80}{Colors.END}")
    
    messages = [
        "כן",
        "על היכולת לשמור על הבת מלך שאני",
        "לא להגרר לויכוחים והורדות ידיים",
        "היום אני מאבדת עשתונות מהר",
        "הייתי רוצה להישאר רגועה",
        "8",
        "אתמול הבת שלי ענתה לבעלי בצורה מזלזלת ואני נכנסתי איתה למאבק כוח",
    ]
    
    state = await simulate_conversation(messages)
    
    # Check last coach message - should be generic, not "מה נאמר?"
    last_coach_msg = ""
    for msg in reversed(state.get("messages", [])):
        if msg.get("sender") == "coach":
            last_coach_msg = msg.get("content", "")
            break
    
    print(f"\n{Colors.BOLD}🔍 בדיקת השאלה האחרונה:{Colors.END}")
    print(f"   {Colors.YELLOW}{last_coach_msg[:150]}{Colors.END}")
    
    if "מה בדיוק נאמר" in last_coach_msg or "מה המילים שנאמרו" in last_coach_msg:
        print(f"   {Colors.RED}❌ שאלה על דיאלוג כשאלה ראשונה{Colors.END}")
    elif "מה עוד קרה" in last_coach_msg or "איך זה התפתח" in last_coach_msg or "ספר לי יותר" in last_coach_msg:
        print(f"   {Colors.GREEN}✅ שאלה גנרית - מצוין!{Colors.END}")
    else:
        print(f"   {Colors.YELLOW}⚠️  שאלה אחרת{Colors.END}")

async def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}🎭 סימולציה לוקלית של תיקוני BSD v2{Colors.END}")
    print(f"{'='*80}\n")
    
    try:
        # Test 1
        await test_s2_to_s4_blocking()
        
        print(f"\n{Colors.YELLOW}{'─'*80}{Colors.END}\n")
        await asyncio.sleep(1)
        
        # Test 2
        await test_s2_questions()
        
        print(f"\n{Colors.BOLD}{'='*80}")
        print(f"✅ סימולציה הסתיימה!")
        print(f"{'='*80}{Colors.END}\n")
        
    except Exception as e:
        print(f"\n{Colors.RED}❌ שגיאה כללית: {e}{Colors.END}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check if Azure OpenAI credentials are set
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print(f"{Colors.RED}❌ חסרים credentials של Azure OpenAI{Colors.END}")
        print(f"{Colors.YELLOW}ℹ️  הגדר את המשתנים:{Colors.END}")
        print(f"   export AZURE_OPENAI_ENDPOINT=...")
        print(f"   export AZURE_OPENAI_API_KEY=...")
        print(f"   export AZURE_OPENAI_DEPLOYMENT_NAME=...")
        sys.exit(1)
    
    asyncio.run(main())
