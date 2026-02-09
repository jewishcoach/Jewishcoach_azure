#!/usr/bin/env python3
"""
Simulation based on expert feedback conversation
Tests if coach properly goes through S6→S7 and asks validation questions
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.bsd_v2.single_agent_coach import handle_conversation
from app.bsd_v2.state_schema_v2 import create_initial_state

# Conversation from expert feedback
CONVERSATION = [
    ("משתמש", "על שמירת הגבולות שלי"),
    ("משתמש", "לפעמים אני לא מצליחה באמת לעשות כרצוני מול ציפיות או רצונות של הסביבה הקרובה"),
    ("משתמש", "יש יומולדת לאמא שלי ואני רוצה לצאת מוקדם לדרך ואני מרגישה שאני צריכה להצדיק את הסיבות בגללן אני יוצאת..."),
    ("משתמש", "בעצם לא רצון שלי שיוצא מהשגרה הרגילה של הבית יכול להתקל בתגובה מחלישה ששמה ספק על הרצון שלי"),
    # S2 - Event request
    ("משתמש", "אז אני רוצה לצאת ליומולדת של אמא שלי ויש לי עוד מלא סידורים לעשות שצברתי לי אז המחשבה שלי היתה כבר לצאת ליום סידורים ואז בעלי שואל אותי מלא שאלות- למה ואיך וכמה... ואני כאילו צריכה לתת כל כך הרבה הסברים על כל דבר שזה מחליש ומערער אותי וגם מעייף"),
    ("משתמש", "היינו בסלון, אמרתי לו שאני יוצאת מוקדם ליומולדת ואז הוא שאל ומה עם הילדים, ומתי את חוזרת ולמה כלכ ך מוקדם ואת יודעת שיש פקקים ואולי לא כדאי וגם האחיות שלך באות מוקדם... עד שהתעצבנתי על השאלות והחפירות ואמרתי לו שיניח לי להחליט בעצמי איך אני עושה ומתי והלכתי עצבנית ונעלבת למטבח"),
    # S3 - Emotions
    ("משתמש", "שהוא לא סומך עלי חושב שאני ילדה קטנה שאפשר להחליט לה וגם שלא איכפת לו ממני רק ממה שנוח לו"),
    ("משתמש", "בסרעפת"),
    ("משתמש", "תסכול, כעס עלבון ועייפות"),
    ("משתמש", "עניתי על זה כבר אולי תמשיך"),
    # S4 - Thought
    ("משתמש", "עניתי כבר- שלא אכפת לו ממני, שהוא חושב שאני קטנה... אלו היו המחשבות.."),
    # S5 - Action
    ("משתמש", "הלכתי למטבח כועסת ונעלבת"),
    # S5 - Desired action
    ("משתמש", "הייתי רוצה לעצור לפני כל השאלות, להגיד בביטחון מה הלוז שלי להיום ולשאול האם הוא צריך ממני משהו לפני שאני יוצאת"),
]

async def run_simulation():
    """Run the simulation based on expert feedback"""
    
    print("=" * 80)
    print("🧪 SIMULATION: Expert Feedback Conversation")
    print("=" * 80)
    print("\n📋 Testing:")
    print("  1. ✅ Coach should proceed to S6 (gap) after S5")
    print("  2. ✅ Coach should proceed to S7 (pattern) after S6")
    print("  3. ✅ Coach should ask validation questions in S7:")
    print("     - 'האם אתה מכיר את עצמך מופיע כך בעוד מקומות?'")
    print("     - 'האם זה קורה רק עם [person/situation]?'")
    print("     - 'האם זה תלוי בנסיבות או במציאות?'")
    print("  4. ✅ Coach should summarize PATTERN (not story) before S8")
    print("\n" + "=" * 80 + "\n")
    
    # Initialize state
    state = create_initial_state(
        conversation_id="test-9999",
        user_id="test-user-9999",
        language="he"
    )
    
    for turn_num, (role, message) in enumerate(CONVERSATION, 1):
        print(f"\n{'─' * 80}")
        print(f"Turn {turn_num}: {role}")
        print(f"{'─' * 80}")
        print(f"💬 Message: {message[:100]}{'...' if len(message) > 100 else ''}")
        
        try:
            # Call coach
            coach_message, state = await handle_conversation(
                user_message=message,
                state=state,
                language="he"
            )
            
            current_stage = state.get("current_step", "?")
            saturation = state.get("saturation_score", 0.0)
            
            print(f"\n🤖 Coach (Stage: {current_stage}, Saturation: {saturation:.2f}):")
            print(f"   {coach_message[:200]}{'...' if len(coach_message) > 200 else ''}")
            
            # Check for critical transitions
            if current_stage == "S6":
                print(f"\n✅ GOOD: Coach moved to S6 (gap)!")
                if "איך תקרא לפער" in coach_message or "תן שם לפער" in coach_message:
                    print(f"✅ GOOD: Coach asks to name the gap!")
                else:
                    print(f"⚠️  WARNING: Coach in S6 but didn't ask to name gap")
            
            elif current_stage == "S7":
                print(f"\n✅ GOOD: Coach moved to S7 (pattern)!")
                
                # Check for validation questions
                validation_questions = [
                    "מכיר את עצמך מופיע כך",
                    "קורה רק עם",
                    "תלוי בנסיבות",
                    "איפה עוד זה קורה",
                    "מאיפה עוד אתה מכיר"
                ]
                
                found_validation = False
                for q in validation_questions:
                    if q in coach_message:
                        print(f"✅ GOOD: Coach asks validation question: '{q}'")
                        found_validation = True
                        break
                
                if not found_validation:
                    print(f"⚠️  WARNING: Coach in S7 but didn't ask validation questions yet")
            
            elif current_stage == "S8":
                print(f"\n✅ GOOD: Coach moved to S8 (gains/losses)!")
                
                # Check if coach summarized pattern (not story)
                if "דפוס" in coach_message:
                    print(f"✅ EXCELLENT: Coach mentions 'דפוס' (pattern)!")
                
                if any(word in coach_message for word in ["באותו רגע", "בסלון", "אמרת לו"]):
                    print(f"⚠️  WARNING: Coach summarizing story details instead of pattern")
            
            # Check if coach is stuck in S5 and trying to end
            if current_stage == "S5" and any(phrase in coach_message for phrase in ["סיכום", "סיימנו", "זה היה"]):
                print(f"\n❌ ERROR: Coach trying to end at S5! Should proceed to S6→S7!")
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            break
    
    print("\n" + "=" * 80)
    print("🏁 SIMULATION COMPLETE")
    print("=" * 80)
    
    # Summary
    final_stage = state.get("current_step", "Unknown")
    print("\n📊 SUMMARY:")
    print(f"  Total turns: {len(CONVERSATION)}")
    print(f"  Final stage: {final_stage}")
    print("\n🔍 Check above for:")
    print("  ✅ Coach moved to S6 (gap)")
    print("  ✅ Coach moved to S7 (pattern)")
    print("  ✅ Coach asked validation questions")
    print("  ✅ Coach summarized pattern (not story)")

if __name__ == "__main__":
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
