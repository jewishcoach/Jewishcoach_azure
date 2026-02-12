#!/usr/bin/env python3
"""Simulate the IMPROVED logic"""

def user_wants_to_continue(msg):
    signals = ["lo kara klum", "katavti lekha", "bo namshikh", "mah akhshav", "di"]
    return any(s in msg.lower() for s in signals)

def has_sufficient_event_details(messages):
    user_msgs = [m["content"] for m in messages if m["sender"] == "user"]
    if len(user_msgs) < 2:
        return False, "need_more"
    total_length = sum(len(m) for m in user_msgs)
    if total_length < 40:
        return False, "too_short"
    detail_words = ["mi", "eifo", "amar", "asa", "kara"]
    if not any(w in " ".join(user_msgs) for w in detail_words):
        return False, "no_details"
    return True, ""

print("=" * 60)
print("Scenario 1: Frustrated WITHOUT enough info")
print("=" * 60)

conv1 = {"messages": [
    {"sender": "coach", "content": "mah kara?"},
    {"sender": "user", "content": "hi tzaaka"}
]}

print("\nUser: 'hi tzaaka' (10 chars, no details)")
print("User: 'lo kara klum, bo namshikh' (frustrated!)")

frustrated = user_wants_to_continue("lo kara klum, bo namshikh")
has_info, reason = has_sufficient_event_details(conv1["messages"])

print(f"\nuser_wants_to_continue(): {frustrated}")
print(f"has_sufficient_event_details(): {has_info} ({reason})")

if frustrated and not has_info:
    print("\n=> EXPLAIN why we need more info!")
    print("   'I understand you want to continue.")
    print("    I need more details to identify your pattern.")
    print("    Who was there? What exactly was said?'")

print("\n" + "=" * 60)
print("Scenario 2: Frustrated WITH enough info")
print("=" * 60)

conv2 = {"messages": [
    {"sender": "coach", "content": "mah kara?"},
    {"sender": "user", "content": "hi tzaaka alai bapgisha"},
    {"sender": "coach", "content": "mah od?"},
    {"sender": "user", "content": "hi amra sheani lo maspik tov veshabos yiten la et haproject"}
]}

print("\nUser gave detailed responses (86 chars total)")
print("User: 'di, bo namshikh'")

frustrated = user_wants_to_continue("di, bo namshikh")
has_info, reason = has_sufficient_event_details(conv2["messages"])

print(f"\nuser_wants_to_continue(): {frustrated}")
print(f"has_sufficient_event_details(): {has_info}")

if frustrated and has_info:
    print("\n=> ALLOW transition to S3!")
    print("   'What did you feel in that moment?'")

print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
print("""
Frustration is a SIGNAL, not a COMMAND!

When frustrated:
1. Check if we have sufficient info
2. If YES => allow transition
3. If NO => EXPLAIN why we need it

Result:
- User understands why the stage is important
- User shares better quality info
- More accurate pattern identification
""")
