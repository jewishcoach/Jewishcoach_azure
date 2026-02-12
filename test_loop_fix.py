#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/ishai/code/Jewishcoach_azure/backend')

from app.bsd_v2.single_agent_coach import (
    user_already_gave_emotions,
    detect_stuck_loop,
    user_wants_to_continue
)

print("Testing loop fixes...")

# Test 1
test1 = {"messages": [
    {"sender": "coach", "content": "mah?"},
    {"sender": "user", "content": "kinaa etzev"}
]}
r1 = user_already_gave_emotions(test1)
print(f"Test 1: {r1} (expected True)")

# Test 2
test2 = {"messages": [
    {"sender": "coach", "content": "mah od"},
    {"sender": "user", "content": "lo"},
    {"sender": "coach", "content": "mah od"},
    {"sender": "user", "content": "lo"}
]}
r2 = detect_stuck_loop(test2)
print(f"Test 2: {r2} (expected True)")

# Test 3
r3 = user_wants_to_continue("lo kara klum")
print(f"Test 3: {r3} (expected True)")

print("Done!")
