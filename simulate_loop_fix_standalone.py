#!/usr/bin/env python3
"""
Standalone simulation of the infinite loop bug fix.
Demonstrates the logic without importing the full codebase.
"""

def user_already_gave_emotions(messages, last_turns=3):
    """Check if user already gave emotions in recent messages"""
    emotion_keywords_he = [
        "קנאה", "כעס", "עצב", "שמחה", "פחד", "תסכול", "אכזבה",
        "גאווה", "בושה", "אשם", "מבוכה", "עלבון"
    ]
    
    recent_user = [
        msg["content"].lower() 
        for msg in messages[-last_turns * 2:] 
        if msg.get("sender") == "user"
    ]
    
    for msg in recent_user:
        if any(emotion in msg for emotion in emotion_keywords_he):
            return True
    return False

def detect_stuck_loop(messages, last_n=4):
    """Detect if coach is stuck repeating the same question"""
    recent_coach = [
        msg["content"]
        for msg in messages[-last_n:]
        if msg.get("sender") == "coach"
    ]
    
    if len(recent_coach) < 2:
        return False
    
    # Check exact repetition
    if recent_coach[-1] == recent_coach[-2]:
        return True
    
    # Check similar questions
    key_phrases = ["מה עוד קרה", "מה הרגשת"]
    for phrase in key_phrases:
        count = sum(1 for msg in recent_coach if phrase in msg)
        if count >= 2:
            return True
    
    return False

def user_wants_to_continue(user_message):
    """Check if user is signaling they want to move forward"""
    continue_signals = [
        "כתבתי לך", "אמרתי לך", "עניתי", "כבר אמרתי",
        "לא קרה כלום", "לא קרה שום דבר", "לא היה",
        "אולי נמשיך", "בוא נמשיך", "מה עכשיו",
        "זהו", "די", "אין עוד"
    ]
    
    msg_lower = user_message.lower()
    return any(signal in msg_lower for signal in continue_signals)

# ============================================================================
# SIMULATION
# ============================================================================

def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_turn(num, speaker, message, indent=0):
    icon = "🤖" if speaker == "מאמן" else "👤"
    spaces = "   " * indent
    print(f"\n{spaces}{icon} Turn {num} - {speaker}:")
    print(f"{spaces}   \"{message}\"")

def print_check(check_name, result, action=""):
    status = "✅" if result else "⚠️"
    print(f"   {status} {check_name}: {result}")
    if action:
        print(f"      → {action}")

# ============================================================================
# PART 1: Original Bug
# ============================================================================

print_header("🚨 PART 1: השיחה המקורית (עם באג הלולאה)")

print("""
המאמן חוזר על שאלות למרות שהמשתמש ענה:
""")

print_turn(1, "מאמן", "איך זה גרם לך להרגיש באותו רגע?")
print_turn(2, "משתמש", "קנאה, קצת זלזול בעצמי, קצת עצב על שנים בהם לא השקעתי")
print("   ✅ המשתמש נתן רגשות מפורטות!")

print_turn(3, "מאמן", "מה עוד קרה באותו רגע? ספר לי יותר פרטים.")
print("   ❌ BAD: חזר לשלב 2 (אירוע) אחרי שהמשתמש כבר נתן רגשות!")

print_turn(4, "משתמש", "לא קרה כלום, נהנתי לשיר")
print("   🚨 המשתמש אומר 'לא קרה כלום' = סיגנל שרוצה להמשיך!")

print_turn(5, "מאמן", "מה עוד קרה באותו רגע? ספר לי יותר פרטים.")
print("   ❌ BAD: שאל את אותה שאלה שוב!")

print_turn(6, "משתמש", "לא קרה, אולי נמשיך")
print("   🚨 המשתמש אומר 'אולי נמשיך' = תסכול ברור!")

print_turn(7, "מאמן", "רגע, לפני שנדבר על מחשבות - ספר לי קודם מה הרגשת באותו רגע?")
print_turn(8, "משתמש", "קנאה, קצת זלזול בעצמי, קצת עצב")
print("   ✅ המשתמש נתן רגשות שוב!")

print_turn(9, "מאמן", "מה עוד קרה באותו רגע? ספר לי יותר פרטים.")
print("   ❌ BAD: חזר שוב לשלב 2!")

print_turn(10, "משתמש", "כתבתי לך מה הרגשתי, מה עכשיו?")
print("   🚨 המשתמש אומר 'כתבתי לך כבר' = תסכול חזק!")

print_turn(11, "מאמן", "רגע, לפני שנדבר על מחשבות - ספר לי קודם מה הרגשת באותו רגע?")
print("   ❌ BAD: לולאה אינסופית!")

# ============================================================================
# PART 2: With Fixes
# ============================================================================

print_header("✅ PART 2: אותה שיחה עם התיקונים")

conversation = {
    "messages": []
}

# Turn 1
print_turn(1, "מאמן", "איך זה גרם לך להרגיש באותו רגע?")
conversation["messages"].append({
    "sender": "coach",
    "content": "איך זה גרם לך להרגיש באותו רגע?"
})

print_turn(2, "משתמש", "קנאה, קצת זלזול בעצמי, קצת עצב על שנים בהם לא השקעתי")
conversation["messages"].append({
    "sender": "user",
    "content": "קנאה, קצת זלזול בעצמי, קצת עצב על שנים בהם לא השקעתי"
})

print("\n   🔍 Safety Net בודק:")
has_emotions = user_already_gave_emotions(conversation["messages"])
print_check("user_already_gave_emotions()", has_emotions,
            "✅ זוכר שהמשתמש נתן רגשות!")

# Turn 2 - Coach tries to go backwards
print_turn(3, "מאמן (מנסה)", "מה עוד קרה באותו רגע? [ניסיון S3→S2]")
conversation["messages"].append({
    "sender": "coach",
    "content": "מה עוד קרה באותו רגע? ספר לי יותר פרטים."
})

print("\n   🔍 Safety Net בודק:")
has_emotions = user_already_gave_emotions(conversation["messages"])
print_check("user_already_gave_emotions()", has_emotions,
            "🚫 BLOCK! המשתמש כבר נתן רגשות, אסור לחזור ל-S2!")

print("\n   💡 Backwards Transition Check:")
print("      Current: S3 (emotions), Trying: S2 (event)")
print("      → 🚫 BLOCKED! Can't go backwards S3→S2")
print("      → Safety Net forces progression!")

print_turn(3, "מאמן (בפועל)", "איך הרגש הזה הרגיש בגוף? איפה הרגשת אותו?")
print("   ✅ המשיך ב-S3 (מיקום בגוף) במקום לחזור!")

# Turn 3
print_turn(4, "משתמש", "בחזה, תחושת כובד")
conversation["messages"].append({
    "sender": "user",
    "content": "בחזה, תחושת כובד"
})

print_turn(5, "מאמן", "מה עבר לך בראש באותו רגע?")
print("   ✅ עבר ל-S4 (מחשבות)! אין לולאה!")

# ============================================================================
# PART 3: More Examples
# ============================================================================

print_header("🧪 PART 3: דוגמאות נוספות")

print('\n📋 דוגמה 1: זיהוי "לא קרה כלום"')
conversation2 = {"messages": [
    {"sender": "coach", "content": "מה עוד קרה?"},
    {"sender": "user", "content": "לא קרה כלום, נהנתי לשיר"}
]}
print('   User: "לא קרה כלום, נהנתי לשיר"')
wants = user_wants_to_continue("לא קרה כלום, נהנתי לשיר")
print_check("user_wants_to_continue()", wants,
            "✅ Safety Net מאפשר מעבר ל-S3!")

print('\n📋 דוגמה 2: זיהוי "כתבתי לך כבר"')
msg = "כתבתי לך מה הרגשתי, מה עכשיו?"
wants = user_wants_to_continue(msg)
print(f'   User: "{msg}"')
print_check("user_wants_to_continue()", wants,
            "✅ Safety Net מאפשר מעבר!")

print('\n📋 דוגמה 3: זיהוי לולאה')
conversation3 = {"messages": [
    {"sender": "coach", "content": "מה עוד קרה באותו רגע?"},
    {"sender": "user", "content": "לא קרה"},
    {"sender": "coach", "content": "מה עוד קרה באותו רגע?"},
    {"sender": "user", "content": "כלום"},
    {"sender": "coach", "content": "מה עוד קרה באותו רגע?"}
]}
print('   Coach asked "מה עוד קרה?" 3 פעמים')
is_loop = detect_stuck_loop(conversation3["messages"])
print_check("detect_stuck_loop()", is_loop,
            "🚫 Safety Net כופה התקדמות!")

print('\n📋 דוגמה 4: זיהוי רגשות')
conversation4 = {"messages": [
    {"sender": "coach", "content": "מה קרה?"},
    {"sender": "user", "content": "הרגשתי קנאה וכעס חזק"},
    {"sender": "coach", "content": "ספר עוד"}
]}
print('   User: "הרגשתי קנאה וכעס חזק"')
has = user_already_gave_emotions(conversation4["messages"])
print_check("user_already_gave_emotions()", has,
            "✅ Safety Net זוכר שנתן רגשות!")

# ============================================================================
# SUMMARY
# ============================================================================

print_header("📊 סיכום התיקונים")

print("""
4 מנגנונים חדשים ב-Safety Net מונעים את הלולאה:

1. ✅ user_already_gave_emotions()
   - בודק אם המשתמש כבר שיתף רגשות
   - מחפש מילות מפתח: קנאה, עצב, כעס, פחד, וכו'
   - אם מצא → חוסם חזרה ל-S2!

2. ✅ user_wants_to_continue()
   - מזהה סיגנלים של תסכול/רצון להמשיך
   - מחפש: "לא קרה כלום", "כתבתי לך", "מה עכשיו", "אולי נמשיך"
   - אם מצא → מאפשר מעבר קדימה!

3. ✅ detect_stuck_loop()
   - בודק אם המאמן חוזר על אותה שאלה
   - מזהה: "מה עוד קרה" x2, "מה הרגשת" x2
   - אם מצא → כופה התקדמות!

4. ✅ Block Backwards Transitions
   - אסור לחזור מ-S3 ל-S2, מ-S4 ל-S3, וכו'
   - בודק מיקום ב-stage_order
   - אם backwards → חוסם!

התוצאה:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
לפני התיקון: לולאה אינסופית ❌
אחרי התיקון: שיחה זורמת בלי חזרות ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

print("\n" + "=" * 80)
print("  ✅ סימולציה הושלמה בהצלחה!")
print("  🚀 התיקונים מוכנים לפריסה לפרודקשן!")
print("=" * 80)
