# הלוגיקה המתוקנת לזיהוי תסכול

## הבעיה עם הלוגיקה הנוכחית

```python
# ❌ WRONG:
if user_wants_to_continue(user_msg):
    return True, None  # מאפשר מעבר בלי בדיקה!
```

זה **מדלג שלבים** אם המשתמש מתוסכל, גם אם השלב לא הושלם!

---

## הלוגיקה הנכונה

תסכול צריך לשמש **אינדיקטור** בלבד. אחר כך צריך לבדוק:

### 1. האם יש מספיק מידע באמת?

```python
def has_sufficient_info_for_s3(state):
    """Check if we have enough event details to move to emotions"""
    messages = state.get("messages", [])
    s2_messages = [
        msg["content"] 
        for msg in messages 
        if msg.get("sender") == "user" and in_stage_s2(msg)
    ]
    
    # Check criteria:
    # - At least 2 user messages in S2
    # - Total length > 50 chars (not just "כן" / "לא")
    # - Some detail words (מי, מה, איך, אמר, עשה)
    
    if len(s2_messages) < 2:
        return False, "צריך לפחות 2 תשובות מהמשתמש"
    
    total_length = sum(len(msg) for msg in s2_messages)
    if total_length < 50:
        return False, "התשובות קצרות מדי"
    
    detail_words = ["מי", "מה", "איך", "אמר", "עשה", "קרה", "הגיב"]
    has_details = any(word in " ".join(s2_messages) for word in detail_words)
    
    if not has_details:
        return False, "חסרים פרטים על האירוע"
    
    return True, None
```

### 2. הסבר למשתמש אם חסר מידע

```python
if user_wants_to_continue(user_msg):
    # User is frustrated - check if we have enough info
    has_info, reason = has_sufficient_info_for_s3(state)
    
    if has_info:
        # We DO have enough → allow transition
        logger.info("[Safety Net] User frustrated but has enough info → allowing")
        return True, None
    else:
        # We DON'T have enough → EXPLAIN why we need it
        logger.warning(f"[Safety Net] User frustrated but missing info: {reason}")
        
        if language == "he":
            return False, (
                "אני מבין שאתה רוצה להמשיך. "
                "אני צריך עוד קצת פרטים על המצב כדי שנוכל לזהות את הדפוס שלך בצורה מדויקת. "
                "ספר לי בבקשה - מי עוד היה שם? מה בדיוק נאמר?"
            )
```

### 3. הלוגיקה המלאה

```python
# S2→S3 transition
if old_step == "S2" and new_step == "S3":
    s2_turns = count_turns_in_step(state, "S2")
    
    # 1. Check if stuck in loop
    if detect_stuck_loop(state):
        return True, None  # Force progression
    
    # 2. Check if user already gave emotions (wrong stage!)
    if user_already_gave_emotions(state):
        return True, None  # Allow transition
    
    # 3. Check if user is frustrated
    user_msg = state.get("messages", [])[-1].get("content", "")
    if user_wants_to_continue(user_msg):
        # User is frustrated - check if we have enough info
        has_info, reason = has_sufficient_event_details(state)
        
        if has_info:
            # Good to go!
            logger.info("[Safety Net] User frustrated, but has sufficient details")
            return True, None
        else:
            # Need more info - EXPLAIN why
            logger.warning(f"[Safety Net] User frustrated, but missing: {reason}")
            return False, get_explanatory_message(reason, language)
    
    # 4. Normal flow - check turns
    if s2_turns < 3:
        # Check if LLM already moved to S3
        if llm_already_in_s3:
            return True, None
        else:
            return False, followup_questions[s2_turns]
```

---

## דוגמה לשיחה

### ❌ הלוגיקה הישנה:

```
Turn 1:
מאמן: "מה קרה?"
משתמש: "היא צעקה"

Turn 2:
מאמן: "מה עוד קרה?"
משתמש: "לא קרה כלום, בוא נמשיך"  ← תסכול

Safety Net (ישן):
→ user_wants_to_continue() = True
→ מאפשר S2→S3  ❌ (אין מספיק פרטים!)
```

### ✅ הלוגיקה החדשה:

```
Turn 1:
מאמן: "מה קרה?"
משתמש: "היא צעקה"  (רק 11 תווים)

Turn 2:
מאמן: "מה עוד קרה?"
משתמש: "לא קרה כלום, בוא נמשיך"  ← תסכול

Safety Net (חדש):
1. user_wants_to_continue() = True  ✓
2. has_sufficient_event_details() = False (חסר: מי? איפה? מה בדיוק אמרה?)
3. → מסביר למשתמש:

מאמן: "אני מבין שאתה רוצה להמשיך. אני צריך עוד קצת פרטים 
       על המצב הספציפי כדי שנוכל לזהות את הדפוס שלך במדויק.
       ספר לי - מי עוד היה שם? מה בדיוק היא אמרה?"
```

---

## סיכום

| מצב | לוגיקה ישנה | לוגיקה חדשה |
|-----|-------------|-------------|
| תסכול + יש מידע | מאפשר מעבר ✓ | בודק → מאפשר מעבר ✓ |
| תסכול + חסר מידע | מאפשר מעבר ❌ | בודק → מסביר למה צריך ✓ |
| אין תסכול + מספיק turns | מאפשר מעבר ✓ | מאפשר מעבר ✓ |
| אין תסכול + מעט turns | שואל שוב ✓ | שואל שוב ✓ |
