"""
BSD Full Session Simulator
===========================
Simulates a complete 11-stage coaching session to test the system end-to-end.

Scenario: Father trying to motivate children to help at home
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.bsd.engine import BsdEngine
from app.models import Conversation, User, BsdSessionState


# Simulated user responses for each stage
SIMULATION_SCRIPT = {
    "S0": "כן, אני מסכים",
    "S1": "אני רוצה להתאמן על הורות - איך להניע את הילדים שלי לעזור בבית",
    "S2": """אתמול בערב ביקשתי מהבן שלי בן ה-12 לאסוף את הכלים מהשולחן אחרי ארוחת ערב. 
    הוא אמר "רגע אבא, אני באמצע משחק" ולא זז. אני חזרתי על הבקשה פעמיים נוספות, 
    הוא המשיך להתעלם. בסוף צעקתי עליו "תקום עכשיו!" והוא קם בכעס, זרק את הכלים בכיור 
    ונעלם לחדר. אשתי הסתכלה עלי במבט מאשים.""",
    "S3": "כעס, תסכול, אשמה, חוסר אונים",
    "S4": "חשבתי לעצמי: 'למה הוא תמיד עושה לי את זה? אני לא מבקש הרבה, רק מעט עזרה בבית!'",
    "S5": "צעקתי עליו בקול רם, אמרתי 'תקום עכשיו!', עמדתי מעליו עד שקם",
    "S6": "הפער בין מי שאני למי שהייתי רוצה להיות - 8. אני קורא לזה 'פער בין דורש לממריץ'",
    "S7": """כן, אני מזהה דפוס חוזר: כל פעם שאני מבקש מהילדים משהו והם לא מגיבים מיד, 
    אני עובר ישר למצב של דרישה וכפייה. האמונה שמפעילה את זה היא 'אם אני לא אהיה נחוש 
    ותקיף, הם לא יעשו כלום ויפנקו אותי'.""",
    "S8": """הייתי רוצה להיות אבא שממריץ ומעורר רצון פנימי, לא אבא שכופה. 
    אבא שהילדים שלו רוצים לעזור כי הם מבינים את החשיבות, לא כי הם פוחדים.""",
    "S9": """כוחות מקור: אמונה שלילדים יש ערך פנימי וחשיבה עצמאית (צלם אלוקים), 
    ערך של חינוך לאחריות ולא רק ציות.
    כוחות טבע: יכולת להסביר ולתקשר בבהירות, סבלנות כשאני רגוע, הבנה פסיכולוגית.""",
    "S10": """אני מבקש להתאמן על הקושי להתמודד עם התנגדות של הילדים לעזרה בבית,
    כך שאפעל מתוך המקור שלי - אמונה ביכולת שלהם - ומתוך הזהות החדשה - אבא ממריץ,
    כדי שהתוצאה המדידה שאשיג תהיה שהילדים יתחילו לעזור מיוזמתם הם לפחות פעמיים בשבוע.""",
}


async def simulate_session():
    """Run a complete simulated coaching session"""
    db = SessionLocal()
    
    try:
        # Create a test user
        test_user = db.query(User).filter(User.email == "test_simulator@example.com").first()
        if not test_user:
            test_user = User(
                clerk_id="sim_test_001",
                email="test_simulator@example.com",
                is_admin=False
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        
        # Create a test conversation
        conv = Conversation(
            user_id=test_user.id,
            title="Simulation: Motivating Children",
            current_phase="S0"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        
        print("=" * 80)
        print("BSD FULL SESSION SIMULATOR")
        print("=" * 80)
        print(f"Scenario: Father trying to motivate children to help at home")
        print(f"Conversation ID: {conv.id}")
        print("=" * 80)
        print()
        
        # Initialize BSD engine
        engine = BsdEngine()
        
        # Track stages
        current_stage = "S0"
        stage_counter = 0
        MAX_TURNS = 10  # Limit simulation to 10 turns
        
        # Welcome message
        print("🤖 COACH: שלום! בשיטת BSD התשובות לא אצלי. האם יש לי רשות להתחיל איתך תהליך?\n")
        
        while current_stage != "S10" and stage_counter < MAX_TURNS:
            stage_counter += 1
            
            # Get user response for current stage
            user_msg = SIMULATION_SCRIPT.get(current_stage)
            if not user_msg:
                print(f"⚠️  No script for stage {current_stage}")
                break
            
            print(f"👤 USER ({current_stage}): {user_msg}\n")
            
            print(f"[DEBUG] Calling BSD engine for stage {current_stage}...")
            
            # Run BSD engine
            coach_response, metadata = await engine.run_turn(
                db=db,
                conversation_id=conv.id,
                user_message=user_msg,
                language="he"
            )
            
            print(f"[DEBUG] Got response from engine")
            
            new_stage = metadata.get("bsd_stage", current_stage)
            phase_changed = metadata.get("phase_changed", False)
            
            print(f"[DEBUG] New stage: {new_stage}, Phase changed: {phase_changed}")
            print(f"🤖 COACH: {coach_response}\n")
            
            if phase_changed:
                print(f"✅ ADVANCED: {current_stage} → {new_stage}")
                print("-" * 80)
                print()
                current_stage = new_stage
            else:
                print(f"🔄 LOOP: Still in {current_stage}")
                print("-" * 80)
                print()
            
            # Check if we reached S10
            if current_stage == "S10" or new_stage == "S10":
                print("=" * 80)
                print("🎉 SESSION COMPLETE! Reached final stage (S10)")
                print("=" * 80)
                break
        
        # Check if we stopped due to turn limit
        if stage_counter >= MAX_TURNS:
            print(f"\n⏸️  Stopped after {MAX_TURNS} turns (limit reached)")
        
        # Show final state
        print("\n" + "=" * 80)
        print("FINAL SESSION STATE")
        print("=" * 80)
        
        bsd_state = db.query(BsdSessionState).filter(
            BsdSessionState.conversation_id == conv.id
        ).first()
        
        if bsd_state:
            print(f"Final Stage: {bsd_state.current_stage}")
            print(f"Metrics: {bsd_state.metrics}")
            print(f"Cognitive Data: {bsd_state.cognitive_data}")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(simulate_session())

