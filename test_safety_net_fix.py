#!/usr/bin/env python3
"""
Test Safety Net Fix: Verify that Safety Net doesn't override good LLM transitions
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.bsd_v2.single_agent_coach import validate_stage_transition

class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_test(name, result, details=""):
    """Print test result"""
    status = f"{Colors.GREEN}✅ PASS{Colors.END}" if result else f"{Colors.RED}❌ FAIL{Colors.END}"
    print(f"{status} {name}")
    if details:
        print(f"    {Colors.YELLOW}{details}{Colors.END}")

def test_s2_to_s3_with_emotion_question():
    """
    Test: LLM asks emotion question → should allow S2→S3 even with low turn count
    """
    print(f"\n{Colors.BOLD}Test 1: S2→S3 with emotion question{Colors.END}")
    
    state = {
        "current_step": "S2",
        "messages": [
            {"sender": "user", "content": "test", "metadata": {"step": "S2"}},
            {"sender": "user", "content": "test2", "metadata": {"step": "S2"}},
        ]
    }
    
    coach_message = "עכשיו אני רוצה להתעמק ברגשות. מה הרגשת באותו רגע?"
    
    is_valid, correction = validate_stage_transition(
        old_step="S2",
        new_step="S3",
        state=state,
        language="he",
        coach_message=coach_message
    )
    
    # Should allow transition because coach already asked S3 question
    test_passed = is_valid and correction is None
    print_test(
        "Allow S2→S3 when LLM asks emotion question",
        test_passed,
        f"is_valid={is_valid}, correction={correction}"
    )
    
    return test_passed

def test_s2_to_s3_without_emotion_question():
    """
    Test: LLM asks generic S2 question → should block S2→S3 with low turn count
    """
    print(f"\n{Colors.BOLD}Test 2: S2→S3 without emotion question (should block){Colors.END}")
    
    state = {
        "current_step": "S2",
        "messages": [
            {"sender": "user", "content": "test", "metadata": {"step": "S2"}},
            {"sender": "user", "content": "test2", "metadata": {"step": "S2"}},
        ]
    }
    
    coach_message = "מה עוד קרה באותו רגע?"
    
    is_valid, correction = validate_stage_transition(
        old_step="S2",
        new_step="S3",
        state=state,
        language="he",
        coach_message=coach_message
    )
    
    # Should block because coach hasn't asked S3 question yet and turn count is low
    test_passed = not is_valid and correction is not None
    print_test(
        "Block S2→S3 when LLM still in S2",
        test_passed,
        f"is_valid={is_valid}, correction present={correction is not None}"
    )
    
    return test_passed

def test_s3_to_s4_with_thought_question():
    """
    Test: LLM asks thought question → should allow S3→S4 even with low turn count
    """
    print(f"\n{Colors.BOLD}Test 3: S3→S4 with thought question{Colors.END}")
    
    state = {
        "current_step": "S3",
        "messages": [
            {"sender": "user", "content": "test", "metadata": {"step": "S3"}},
            {"sender": "user", "content": "test2", "metadata": {"step": "S3"}},
        ]
    }
    
    coach_message = "מה עבר לך בראש באותו רגע?"
    
    is_valid, correction = validate_stage_transition(
        old_step="S3",
        new_step="S4",
        state=state,
        language="he",
        coach_message=coach_message
    )
    
    # Should allow transition because coach already asked S4 question
    test_passed = is_valid and correction is None
    print_test(
        "Allow S3→S4 when LLM asks thought question",
        test_passed,
        f"is_valid={is_valid}, correction={correction}"
    )
    
    return test_passed

def test_s3_to_s4_without_thought_question():
    """
    Test: LLM asks for more emotions → should block S3→S4 with low turn count
    """
    print(f"\n{Colors.BOLD}Test 4: S3→S4 without thought question (should block){Colors.END}")
    
    state = {
        "current_step": "S3",
        "messages": [
            {"sender": "user", "content": "test", "metadata": {"step": "S3"}},
            {"sender": "user", "content": "test2", "metadata": {"step": "S3"}},
        ]
    }
    
    coach_message = "מה עוד הרגשת?"
    
    is_valid, correction = validate_stage_transition(
        old_step="S3",
        new_step="S4",
        state=state,
        language="he",
        coach_message=coach_message
    )
    
    # Should block because coach hasn't asked S4 question yet
    test_passed = not is_valid and correction is not None
    print_test(
        "Block S3→S4 when LLM still in S3",
        test_passed,
        f"is_valid={is_valid}, correction present={correction is not None}"
    )
    
    return test_passed

def test_conversation_flow_simulation():
    """
    Simulate the actual conversation flow from the bug report
    """
    print(f"\n{Colors.BOLD}Test 5: Simulate actual conversation flow{Colors.END}")
    
    # Turn 1: In S2, 2 turns
    state_turn1 = {
        "current_step": "S2",
        "messages": [
            {"sender": "user", "content": "דברו על פוליטיקה", "metadata": {"step": "S2"}},
            {"sender": "user", "content": "אמרתי משהו קטן", "metadata": {"step": "S2"}},
        ]
    }
    
    coach_msg_turn1 = "מה בדיוק אמרת? איך החברים הגיבו?"
    
    is_valid_1, _ = validate_stage_transition("S2", "S3", state_turn1, "he", coach_msg_turn1)
    step_1_result = not is_valid_1  # Should block (still asking S2 questions)
    print_test(
        "Turn 1: Block S2→S3 (still exploring event)",
        step_1_result
    )
    
    # Turn 2: User answers, LLM tries to move to S3
    state_turn2 = {
        "current_step": "S2",
        "messages": [
            {"sender": "user", "content": "דברו על פוליטיקה", "metadata": {"step": "S2"}},
            {"sender": "user", "content": "אמרתי משהו קטן", "metadata": {"step": "S2"}},
            {"sender": "user", "content": "החברים המשיכו הלאה", "metadata": {"step": "S2"}},
        ]
    }
    
    coach_msg_turn2 = "עכשיו אני רוצה להתעמק ברגשות. מה הרגשת?"
    
    is_valid_2, correction_2 = validate_stage_transition("S2", "S3", state_turn2, "he", coach_msg_turn2)
    step_2_result = is_valid_2 and correction_2 is None  # Should allow (asked S3 question!)
    print_test(
        "Turn 2: Allow S2→S3 (LLM asked emotion question)",
        step_2_result,
        f"This prevents the bug! LLM's good question is not overridden."
    )
    
    # Turn 3: User in S3, responds with emotion
    state_turn3 = {
        "current_step": "S3",
        "messages": [
            {"sender": "user", "content": "הרגשתי נעלב", "metadata": {"step": "S3"}},
        ]
    }
    
    coach_msg_turn3 = "מה עוד הרגשת?"
    
    is_valid_3, _ = validate_stage_transition("S3", "S4", state_turn3, "he", coach_msg_turn3)
    step_3_result = not is_valid_3  # Should block (only 1 turn in S3)
    print_test(
        "Turn 3: Block S3→S4 (need more emotions)",
        step_3_result
    )
    
    return step_1_result and step_2_result and step_3_result

def main():
    print(f"\n{Colors.BOLD}{'='*80}")
    print("🧪 Testing Safety Net Fix: Prevent Overriding Good LLM Transitions")
    print(f"{'='*80}{Colors.END}\n")
    
    tests = [
        test_s2_to_s3_with_emotion_question(),
        test_s2_to_s3_without_emotion_question(),
        test_s3_to_s4_with_thought_question(),
        test_s3_to_s4_without_thought_question(),
        test_conversation_flow_simulation(),
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"\n{Colors.BOLD}{'='*80}")
    if passed == total:
        print(f"{Colors.GREEN}✅ All tests passed! ({passed}/{total}){Colors.END}")
    else:
        print(f"{Colors.RED}❌ Some tests failed ({passed}/{total}){Colors.END}")
    print(f"{'='*80}{Colors.END}\n")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
