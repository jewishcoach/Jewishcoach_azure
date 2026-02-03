#!/usr/bin/env python3
"""
Full BSD Coaching Session Simulator
=====================================

Simulates a complete coaching session from S0 to S10, showing:
- What the coach says
- What the user responds  
- Stage transitions
- Issues/bottlenecks

This helps identify which stages need improvement.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

sys.path.insert(0, str(Path(__file__).parent))

from app.bsd.reasoner import decide
from app.bsd.stage_defs import StageId, next_stage
from app.bsd.state_schema import BsdState, CognitiveData, EventActual
from app.bsd.talker import generate_coach_message
from app.bsd.scripts import get_script


class SessionSimulator:
    """Simulates a full BSD coaching session."""
    
    def __init__(self, language: str = "he", user_name: str = "Ishai", user_gender: str = "male"):
        self.language = language
        self.user_name = user_name
        self.user_gender = user_gender
        self.current_stage = "S0"
        self.cognitive_data = CognitiveData()
        self.turn_count = 0
        self.max_turns = 30  # Safety limit
        
    def print_separator(self, char="=", length=80):
        """Print a visual separator."""
        print(char * length)
    
    def print_stage_header(self, stage: str, stage_name: str):
        """Print stage transition header."""
        self.print_separator("=")
        print(f"📍 STAGE {stage}: {stage_name}")
        self.print_separator("=")
    
    def print_turn(self, role: str, message: str):
        """Print a conversation turn."""
        icon = "🤖" if role == "coach" else "👤"
        color = "\033[94m" if role == "coach" else "\033[92m"
        reset = "\033[0m"
        
        print(f"\n{icon} {color}{role.upper()}{reset}")
        print(f"   {message[:200]}{'...' if len(message) > 200 else ''}")
    
    def print_decision_info(self, decision_data: Dict[str, Any]):
        """Print decision analysis."""
        print(f"\n   🔍 Intent: {decision_data.get('intent', 'N/A')}")
        print(f"   🎯 Decision: {decision_data.get('decision', 'N/A')}")
        if decision_data.get('critique'):
            print(f"   💬 Critique: {decision_data['critique'][:100]}")
        if decision_data.get('extracted'):
            print(f"   📦 Extracted: {list(decision_data['extracted'].keys())}")
    
    async def run_turn(self, user_message: str) -> tuple[str, bool]:
        """
        Run one conversation turn.
        
        Returns:
            (coach_response, should_continue)
        """
        self.turn_count += 1
        
        if self.turn_count > self.max_turns:
            print(f"\n⚠️  Reached max turns ({self.max_turns}), stopping simulation")
            return "Session ended (max turns)", False
        
        # Print user message
        self.print_turn("user", user_message)
        
        # Run reasoner
        try:
            decision = await decide(
                stage=self.current_stage,
                user_message=user_message,
                language=self.language,
                cognitive_data=self.cognitive_data.model_dump()
            )
        except Exception as e:
            print(f"\n   ❌ Reasoner error: {e}")
            return f"Error: {e}", False
        
        # Print decision info
        self.print_decision_info({
            "intent": decision.intent,
            "decision": decision.decision,
            "critique": decision.critique,
            "extracted": decision.extracted
        })
        
        # Update cognitive data with extractions
        self._merge_extracted_data(decision.extracted)
        
        # Check if we should advance
        should_advance = decision.decision == "advance"
        old_stage = self.current_stage
        
        if should_advance and decision.next_stage:
            self.current_stage = decision.next_stage
        
        # Generate coach response
        try:
            coach_msg, _ = await generate_coach_message(
                stage=self.current_stage,
                user_message=user_message,
                language=self.language,
                intent=decision.intent,
                critique=decision.critique,
                is_loop=not should_advance,
                missing=decision.missing,
                cognitive_data=self.cognitive_data.model_dump(),
                user_name=self.user_name,
                user_gender=self.user_gender,
                recent_openers=[]
            )
        except Exception as e:
            print(f"\n   ❌ Talker error: {e}")
            # Fallback to script
            try:
                coach_msg = get_script(self.current_stage, language=self.language, gender=self.user_gender)
            except:
                coach_msg = "שמעתי אותך." if self.language == "he" else "I hear you."
        
        # Print coach response
        self.print_turn("coach", coach_msg)
        
        # Print stage transition if happened
        if should_advance and old_stage != self.current_stage:
            print(f"\n   ✅ Advanced: {old_stage} → {self.current_stage}")
        
        # Check if we're done
        is_done = self.current_stage == "S10" and should_advance
        
        return coach_msg, not is_done
    
    def _merge_extracted_data(self, extracted: Dict[str, Any]):
        """Merge extracted data into cognitive_data."""
        if not extracted:
            return
        
        # Topic
        if "topic" in extracted:
            self.cognitive_data.topic = extracted["topic"]
        
        # Emotions (accumulate)
        if "emotions_list" in extracted:
            self.cognitive_data.event_actual.emotions_list = extracted["emotions_list"]
        
        # Thought
        if "thought" in extracted:
            self.cognitive_data.event_actual.thought_content = extracted["thought"]
        
        # Action
        if "action_actual" in extracted:
            self.cognitive_data.event_actual.action_content = extracted["action_actual"]
        if "action_desired" in extracted:
            self.cognitive_data.event_desired.action_content = extracted["action_desired"]
        
        # Gap
        if "gap_name" in extracted:
            self.cognitive_data.gap_analysis.name = extracted["gap_name"]
        if "gap_score" in extracted:
            self.cognitive_data.gap_analysis.score = extracted["gap_score"]
    
    def get_stage_name(self, stage: str) -> str:
        """Get Hebrew name for stage."""
        names = {
            "S0": "רשות",
            "S1": "נושא",
            "S2": "אירוע",
            "S3": "רגשות",
            "S4": "מחשבה",
            "S5": "מעשה",
            "S6": "פער",
            "S7": "דפוס",
            "S8": "זהות",
            "S9": "כוחות",
            "S10": "מחויבות"
        }
        return names.get(stage, stage)
    
    async def run_session(self, scenario: list[tuple[str, str]]):
        """
        Run a full session with predefined user responses.
        
        Args:
            scenario: List of (stage_expected, user_message) tuples
        """
        print("\n" + "🎬" * 40)
        print("   BSD COACHING SESSION SIMULATOR")
        print("🎬" * 40)
        
        self.print_stage_header(self.current_stage, self.get_stage_name(self.current_stage))
        
        # Get initial coach message (S0 script)
        try:
            initial_msg = get_script(self.current_stage, language=self.language, gender=self.user_gender)
            self.print_turn("coach", initial_msg)
        except Exception as e:
            print(f"❌ Error getting initial script: {e}")
        
        # Run through scenario
        for expected_stage, user_msg in scenario:
            print(f"\n{'─' * 80}")
            
            # Run turn
            coach_response, should_continue = await self.run_turn(user_msg)
            
            # Check if we're in expected stage (warning if not)
            if self.current_stage != expected_stage:
                print(f"\n   ⚠️  Stage mismatch! Expected {expected_stage}, got {self.current_stage}")
            
            if not should_continue:
                break
            
            # Small delay for readability
            await asyncio.sleep(0.1)
        
        # Final summary
        self.print_separator("=")
        print(f"\n✅ Session completed!")
        print(f"   Total turns: {self.turn_count}")
        print(f"   Final stage: {self.current_stage}")
        print(f"   Topic: {self.cognitive_data.topic or 'N/A'}")
        print(f"   Emotions: {', '.join(self.cognitive_data.event_actual.emotions_list[:4]) if self.cognitive_data.event_actual.emotions_list else 'N/A'}")
        self.print_separator("=")


async def main():
    """Run the simulation with a realistic scenario."""
    
    # Define a realistic coaching scenario
    scenario = [
        # S0: Permission
        ("S0", "כן, יש לך רשות"),
        
        # S1: Topic
        ("S1", "עמידה ביעדים"),
        
        # S2: Event (might need multiple turns)
        ("S2", "יש פרויקט שאני עובד עליו"),
        ("S2", "אתמול בערב ישבתי מול המחשב וניסיתי לעבוד על הפרויקט, אבל לא הצלחתי להתקדם"),
        
        # S3: Emotions (accumulate to 4+)
        ("S3", "כעס"),
        ("S3", "תסכול, יאוש"),
        ("S3", "עצב"),
        
        # S4: Thought
        ("S4", "אני אפסס"),
        
        # S5: Action (actual + desired)
        ("S5", "פשוט סגרתי את המחשב והלכתי"),
        ("S5", "הייתי רוצה לקחת נשימה עמוקה ולומר לעצמי שזה בסדר, שאני יכול לנסות מחר"),
        
        # S6: Gap
        ("S6", "הפער בין להיות תקוע לבין להיות סבלני, 7"),
        
        # S7: Pattern
        ("S7", "זה קורה לי כל פעם שיש לי משימה קשה - אני מרגיש שאני חייב להצליח מיד, ואז נכשל"),
        ("S7", "האמונה שלי היא שאם אני לא מצליח מיד, אני לא מספיק טוב"),
        
        # S8: Being/Identity
        ("S8", "אני רוצה להיות אדם שסבלני עם עצמו, שיודע שלמידה לוקחת זמן"),
        
        # S9: KaMaZ forces
        ("S9", "כוחות המקור שלי: סקרנות, רצון ללמוד, התמדה"),
        ("S9", "כוחות הטבע: הזמן שצריך לכל דבר, הלמידה בתהליך"),
        
        # S10: Commitment
        ("S10", "אני מתאמן על סבלנות עצמית, כדי שאוכל לראות את התהליך ולא רק את התוצאה"),
    ]
    
    # Run simulation
    simulator = SessionSimulator(language="he", user_name="Ishai", user_gender="male")
    
    try:
        await simulator.run_session(scenario)
        return 0
    except Exception as e:
        print(f"\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)




