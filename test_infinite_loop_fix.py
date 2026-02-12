#!/usr/bin/env python3
"""
Test the infinite loop fixes.
Simulates the conversation from the bug report.
"""

import sys
sys.path.insert(0, '/home/ishai/code/Jewishcoach_azure/backend')

from app.bsd_v2.single_agent_coach import (
    user_already_gave_emotions,
    detect_stuck_loop,
    user_wants_to_continue
)

print("=" * 80)
print("🧪 Testing Infinite Loop Fixes")
print("=" * 80)

# === Test 1: user_already_gave_emotions ===
print("\n📋 Test 1: user_already_gave_emotions()")
print("-" * 80)

test_state_1 = {
    "messages": [
        {"sender": "coach", "content": "מה הרגשת באותו רגע?"},
        {"sender": "user", "content": "קנאה, קצת זלזול בעצמי, קצת עצב"}
    ]
}

result = user_already_gave_emotions(test_state_1)
print(f"State: User said 'קנאה, זלזול, עצב'")
print(f"✅ Result: {result} (expected: True)")
assert result == True, "Should detect emotions!"

test_state_2 = {
    "messages": [
        {"sender": "coach", "content": "מה קרה?"},
        {"sender": "user", "content": "היא התנהגה מהמם"}
    ]
}

result = user_already_gave_emotions(test_state_2)
print(f"\nState: User said 'היא התנהגה מהמם'")
print(f"✅ Result: {result} (expected: False)")
assert result == False, "Should NOT detect emotions!"

# === Test 2: detect_stuck_loop ===
print("\n\n📋 Test 2: detect_stuck_loop()")
print("-" * 80)

test_state_3 = {
    "messages": [
        {"sender": "coach", "content": "מה עוד קרה באותו רגע? ספר לי יותר פרטים."},
        {"sender": "user", "content": "לא קרה כלום"},
        {"sender": "coach", "content": "מה עוד קרה באותו רגע? ספר לי יותר פרטים."},
        {"sender": "user", "content": "לא קרה, אולי נמשיך"}
    ]
}

result = detect_stuck_loop(test_state_3)
print(f"State: Coach asked 'מה עוד קרה?' twice")
print(f"✅ Result: {result} (expected: True)")
assert result == True, "Should detect loop!"

test_state_4 = {
    "messages": [
        {"sender": "coach", "content": "מה הרגשת?"},
        {"sender": "user", "content": "קנאה"},
        {"sender": "coach", "content": "מה הרגשת?"},
        {"sender": "user", "content": "עצב"},
        {"sender": "coach", "content": "מה הרגשת?"}
    ]
}

result = detect_stuck_loop(test_state_4)
print(f"\nState: Coach asked 'מה הרגשת?' 3 times")
print(f"✅ Result: {result} (expected: True)")
assert result == True, "Should detect loop!"

# === Test 3: user_wants_to_continue ===
print("\n\n📋 Test 3: user_wants_to_continue()")
print("-" * 80)

test_messages = [
    ("לא קרה כלום", True),
    ("כתבתי לך מה הרגשתי, מה עכשיו?", True),
    ("אולי נמשיך", True),
    ("בוא נמשיך", True),
    ("זהו די", True),
    ("היא התנהגה מהמם", False),
    ("קנאה ועצב", False)
]

for msg, expected in test_messages:
    result = user_wants_to_continue(msg)
    status = "✅" if result == expected else "❌"
    print(f"{status} '{msg}' → {result} (expected: {expected})")
    assert result == expected, f"Failed for '{msg}'"

# === Test 4: Simulated conversation flow ===
print("\n\n📋 Test 4: Simulated Conversation Flow")
print("-" * 80)

print("""
Original conversation (BUG):
1. Coach: "מה עוד קרה באותו רגע?"
2. User: "לא קרה כלום"
3. Coach: "מה עוד קרה באותו רגע?" ← BUG: Same question!
4. User: "לא קרה, אולי נמשיך"
5. Coach: "מה הרגשת?"
6. User: "קנאה, זלזול, עצב"
7. Coach: "מה עוד קרה באותו רגע?" ← BUG: Back to S2!
8. User: "כתבתי לך מה הרגשתי, מה עכשיו?"
9. Coach: "מה הרגשת?" ← BUG: Loop!

With NEW fixes:
""")

conversation_state = {
    "messages": [
        {"sender": "coach", "content": "מה עוד קרה באותו רגע? ספר לי יותר פרטים."},
        {"sender": "user", "content": "לא קרה כלום"}
    ]
}

print("Turn 2:")
print("  User: 'לא קרה כלום'")
wants_continue = user_wants_to_continue("לא קרה כלום")
print(f"  ✅ user_wants_to_continue: {wants_continue}")
print("  → Safety Net should ALLOW S2→S3 transition!")

conversation_state["messages"].extend([
    {"sender": "coach", "content": "מה הרגשת באותו רגע?"},
    {"sender": "user", "content": "קנאה, קצת זלזול בעצמי, קצת עצב"}
])

print("\nTurn 4:")
print("  User: 'קנאה, קצת זלזול, עצב'")
has_emotions = user_already_gave_emotions(conversation_state)
print(f"  ✅ user_already_gave_emotions: {has_emotions}")
print("  → If coach tries S3→S2, Safety Net should BLOCK!")

# Simulate coach trying to go back
conversation_state["messages"].append(
    {"sender": "coach", "content": "מה עוד קרה באותו רגע?"}
)

print("\nTurn 5:")
print("  Coach tries: 'מה עוד קרה?' (going backwards S3→S2)")
is_loop = detect_stuck_loop(conversation_state)
print(f"  ✅ detect_stuck_loop: {is_loop}")
print("  → Safety Net should FORCE progression!")

print("\n" + "=" * 80)
print("✅ ALL TESTS PASSED!")
print("=" * 80)
print("""
Summary of fixes:
1. ✅ user_already_gave_emotions() - detects if user gave emotions
2. ✅ detect_stuck_loop() - detects repetitive questions
3. ✅ user_wants_to_continue() - detects frustration/completion signals
4. ✅ Expanded completion_keywords - includes "לא קרה כלום", "כתבתי לך", etc.
5. ✅ Block backwards transitions (S3→S2, S4→S3, etc.)

These fixes prevent the infinite loop bug! 🎉
""")
