# חקירה לעומק - 4 באגים

## 🔍 **א) זיהוי רגשות צריך להיות מבוסס LLM**

### **הבעיה עם רשימת מילים:**
```python
# ❌ נוכחי - רשימה סטטית:
emotion_keywords = ["קנאה", "כעס", "עצב"...]

# המשתמש אמר: "רע", "חנוק", "נזהר", "לא טבעי"
# → אף מילה לא נמצאה!
```

### **למה רשימה לא טובה:**
1. יש **מאות** דרכים לבטא רגש
2. אנשים משתמשים במילים **לא סטנדרטיות**: "חנוק", "לא טבעי", "כבד", "דחוס"
3. לפעמים זה **משפט**: "הרגשתי שאני לא יכול לזרום"
4. רשימה תמיד תהיה **חסרה**

### **הפתרון - LLM based:**
```python
async def user_already_gave_emotions_llm(state, llm):
    """Use LLM to detect if user shared emotions (smart detection)"""
    
    recent_user = [
        msg["content"] 
        for msg in state["messages"][-6:] 
        if msg["sender"] == "user"
    ]
    
    if not recent_user:
        return False
    
    # Quick prompt to LLM
    prompt = f"""
האם במסרים האחרונים הבאים המשתמש שיתף **רגשות**?

רגשות = דברים כמו: כעס, עצב, שמחה, פחד, קנאה, תסכול, רע, טוב, חנוק, נזהר, וכו'

מסרים:
{chr(10).join(f"- {msg}" for msg in recent_user)}

ענה רק: כן או לא
"""
    
    messages = [
        SystemMessage(content="אתה עוזר שמזהה רגשות בטקסט."),
        HumanMessage(content=prompt)
    ]
    
    response = await llm.ainvoke(messages)
    answer = response.content.strip().lower()
    
    return "כן" in answer or "yes" in answer
```

---

## 🔍 **ב) לא שאל על רגש ומחשבה רצויים**

### **הבעיה:**
הפרומפט מציין רק:
```
S5: מה עשית (מצוי) → מה רצית לעשות (רצוי)
```

**חסר:** רגש רצוי, מחשבה רצויה

### **הפתרון - עדכן פרומפט:**
```
**S5 (מעשה + רצוי - חקור 3 ממדים):**

🎯 **סדר חשוב:**
1. קודם: מצוי (מה עשית בפועל)
2. רק אז: רצוי (איך רצית שזה יהיה)

**חקור את כל 3 הממדים (אם רלוונטי):**

**א) פעולה (חובה!):**
- "מה עשית בפועל באותו רגע?"
- "מה היית רוצה לעשות במקום זה?"

**ב) רגש (אופציונלי - רק אם לא היה ברור ב-S3):**
- אם ב-S3 המשתמש אמר "הרגשתי רע" ולא הרחיב על איך רצה להרגיש
- שאל: "איך היית רוצה להרגיש באותו רגע?"

**ג) מחשבה (אופציונלי - רק אם לא היתה ברורה ב-S4):**
- אם ב-S4 המשתמש נתן מחשבה מצוי אבל לא ברור מה רצה לחשוב
- שאל: "מה היית רוצה לומר לעצמך?"

**⚠️ חשוב:** אל תשאל על כל 3 תמיד!
שאל רק על **מה שחסר** או לא ברור מהשלבים הקודמים.

**דוגמה טובה:**
```
S3: "הרגשתי רע וחנוק"
S4: "אמרתי לעצמי 'תזהר'"
S5: "מה עשית?" → "הקשבתי בשקט"
     "מה רצית לעשות?" → "לדבר בחופשיות"
     
✅ מספיק! יש פעולה מצוי/רצוי ברור
❌ אין צורך: "איך רצית להרגיש?" (כבר ברור מ-S3 שרצה להרגיש טוב)
```

**דוגמה שצריך יותר:**
```
S3: "הרגשתי רע"
S4: "חשבתי שאני לא טוב מספיק"
S5: "מה עשית?" → "לא אמרתי כלום"
     "מה רצית לעשות?" → "להגיד את דעתי"
     
⚠️ לא ברור איך רצה להרגיש!
✅ שאל: "איך היית רוצה להרגיש באותו רגע במקום להרגיש רע?"
```
```

---

## 🔍 **ג) למה חזר מ-S8 ל-S7? החקירה המעמיקה**

### **תיאוריה 1: ה-LLM לא עדכן current_step**

```
מה קרה:
Turn N: מאמן שאל "מה אתה מרוויח?"  ← שאלת S8!
        אבל ב-JSON: "current_step": "S7"  ← לא עדכן!

State נשאר: S7
        
Turn N+1: מאמן חושב שהוא עדיין ב-S7
          → שואל "איפה עוד?"
```

**זו הבעיה!** ה-LLM שואל שאלה של שלב חדש אבל **שוכח לעדכן** את `current_step` ב-JSON!

### **איך לאבחן:**
צריך logs! בלוג אמור להיות:
```
[BSD V2] Parsed internal_state: {"current_step": "S7", ...}
[BSD V2] Parsed internal_state: {"current_step": "S7", ...}  ← עדיין S7!
```

### **הפתרון:**
Safety Net צריך לזהות **mismatch** בין השאלה לבין ה-current_step:

```python
def detect_stage_question_mismatch(coach_message, current_step):
    """Detect if coach asked a question from a different stage"""
    
    stage_questions = {
        "S7": ["איפה עוד", "מאיפה עוד", "where else"],
        "S8": ["מה אתה מרוויח", "מה מפסיד", "what do you gain", "what do you lose"],
        "S9": ["איזה ערך", "what value", "what ability"]
    }
    
    for stage, indicators in stage_questions.items():
        if stage != current_step:
            if any(q in coach_message for q in indicators):
                logger.error(f"[Mismatch] Coach asked {stage} question but current_step={current_step}!")
                return stage  # Return the correct stage
    
    return None
```

**שימוש:**
```python
# After LLM response:
mismatch = detect_stage_question_mismatch(coach_message, state["current_step"])
if mismatch:
    logger.warning(f"[Safety Net] Correcting stage: {state['current_step']} → {mismatch}")
    internal_state["current_step"] = mismatch
```

---

## 🔍 **ד) למה חזר "איפה עוד" 3 פעמים? חקירה מעמיקה**

### **הבעיה המדויקת:**

בשורה 1394:
```python
s7_turns = count_turns_in_step(state, "S7")
if s7_turns < 3:  # ← רק ספירת turns!
    return False, "איפה עוד?"
```

**מה קרה בשיחה:**
```
Turn 1 (S7): "האם אתה מזהה...?"
              → "כן האמת שכן"
              
Turn 2: "דוגמה נוספת?"
        → "עם חברים על פוליטיקה... אין לי כוח להכנס לוויכוח"
        ✅ דוגמה מפורטת!
        
Turn 3: "עוד דוגמאות?"
        → "בעבודה, אני נוטה להסכים... אני לא אוהב עימותים"
        ✅ עוד דוגמה מפורטת!
        
Turn 4 (S7): s7_turns = 4, אבל...
             מאמן: "איפה עוד?"  ← למה?!
             
Turn 5: משתמש: "אבל אמרתי כבר, זה מופיע בעבודה וגם עם חברים"
        
Turn 6: מאמן: "מצטער! איפה עוד זה קורה?"  ← שוב!!!
```

### **למה זה קרה:**

1. **Safety Net בודק רק TURNS, לא CONTENT!**
   - היו 4 turns אבל Safety Net לא **קרא** מה המשתמש אמר
   - לא זיהה ש-**כבר יש 2 דוגמאות**!

2. **אין זיהוי "המשתמש נתן רשימה"**
   - המשתמש אמר: "עם חברים... בעבודה"
   - זה **2 דוגמאות במשפט אחד**!
   - Safety Net לא זיהה

3. **הלוגיקה של detect_stuck_loop לא תפסה**
   - שאל "איפה עוד" פעמיים
   - אבל detect_stuck_loop מחפש **4 הודעות אחרונות**
   - אולי היו הודעות ביניים שמנעו זיהוי

### **הפתרון הנכון:**

צריך לספור **דוגמאות**, לא turns!

```python
def count_pattern_examples_in_s7(state):
    """Count how many pattern examples user gave in S7"""
    
    messages = state.get("messages", [])
    
    # Get user messages in S7
    user_msgs_s7 = [
        msg["content"]
        for msg in messages[-12:]  # Last 12 messages
        if msg.get("sender") == "user"
    ]
    
    example_count = 0
    all_text = " ".join(user_msgs_s7)
    
    # Method 1: Count "למשל", "גם", "עוד"
    example_count += all_text.count("למשל")
    example_count += all_text.count(" גם ")
    example_count += all_text.count("וגם")
    example_count += all_text.count("עוד ")
    
    # Method 2: Count location/context words
    locations = ["עם", "ב", "כש", "אצל"]
    for loc in locations:
        # Count how many times (rough estimate)
        example_count += all_text.count(f"{loc} ") // 2
    
    # Method 3: Check explicit lists
    if "בעבודה" in all_text:
        example_count += 1
    if any(word in all_text for word in ["חברים", "משפחה", "בן זוג"]):
        example_count += 1
    
    return min(example_count, 5)  # Cap at 5


def user_said_multiple_places(user_message):
    """Check if user explicitly said they gave examples"""
    phrases = [
        "אמרתי כבר", "כבר נתתי", "נתתי לך",
        "זה מופיע ב", "זה קורה ב",
        "בהרבה מקומות", "בכל מקום"
    ]
    return any(p in user_message for p in phrases)
```

**שימוש ב-Safety Net:**
```python
# S7→S8: Need pattern confirmation
if old_step == "S7" and new_step == "S8":
    s7_turns = count_turns_in_step(state, "S7")
    
    # 🚨 NEW: Check if user already gave multiple examples
    example_count = count_pattern_examples_in_s7(state)
    user_msg = state.get("messages", [])[-1].get("content", "")
    
    if example_count >= 2 and user_said_multiple_places(user_msg):
        logger.info(f"[Safety Net] User gave {example_count} examples + said 'already told' → allowing S7→S8")
        return True, None  # Allow transition!
    
    # Check for stuck loop
    if detect_stuck_loop(state):
        logger.error(f"[Safety Net] LOOP in S7 with {example_count} examples → forcing S8")
        return True, None
    
    # Normal flow
    if s7_turns < 3:
        return False, pattern_questions[s7_turns]
```

---

## 🔍 **ג) למה חזר מ-S8 ל-S7? הממצא**

### **הבעיה: LLM לא עדכן current_step!**

```
Turn N:
  LLM שאל: "מה אתה מרוויח מהדפוס הזה?"  ← שאלת S8!
  אבל JSON: {"current_step": "S7"}  ← לא עדכן ל-S8!
  
State:
  current_step = "S7"  ← נשאר!

Turn N+1:
  LLM חושב: "אני ב-S7, אז אשאל שאלת S7"
  → "איפה עוד זה קורה?"
```

**זו בעיית CONSISTENCY!**  
ה-LLM לפעמים **מתקדם בתוכן** אבל **לא מעדכן** את current_step ב-JSON!

### **למה זה קורה:**

1. **הפרומפט מורכב** - יש הרבה הוראות
2. **ה-LLM שוכח** לעדכן את current_step
3. **אין בדיקת consistency** בין התוכן (שאלה) לבין current_step

### **הפתרון:**

```python
def detect_stage_question_mismatch(coach_message, current_step, language="he"):
    """Detect if coach asked question from different stage than current_step"""
    
    if language == "he":
        stage_indicators = {
            "S2": ["מה קרה", "מתי זה היה", "מי היה שם"],
            "S3": ["מה הרגשת", "איזה רגש", "איפה הרגשת"],
            "S4": ["מה עבר לך בראש", "מה חשבת", "מה אמרת לעצמך"],
            "S5": ["מה עשית", "מה היית רוצה לעשות"],
            "S6": ["איך תקרא לפער", "בסולם"],
            "S7": ["איפה עוד", "מאיפה עוד", "האם אתה מזהה"],
            "S8": ["מה אתה מרוויח", "מה אתה מפסיד", "מה ההפסד"],
            "S9": ["איזה ערך", "איזו יכולת"],
            "S10": ["איזו עמדה", "מה אתה בוחר"]
        }
    else:
        stage_indicators = {
            "S2": ["what happened", "when was", "who was there"],
            "S3": ["what did you feel", "what emotion"],
            "S4": ["what went through", "what did you think"],
            "S5": ["what did you do", "what would you want"],
            "S6": ["what would you call", "on a scale"],
            "S7": ["where else", "do you recognize"],
            "S8": ["what do you gain", "what do you lose"],
            "S9": ["what value", "what ability"],
            "S10": ["what stance", "what do you choose"]
        }
    
    coach_lower = coach_message.lower()
    
    for stage, indicators in stage_indicators.items():
        if any(ind in coach_lower for ind in indicators):
            if stage != current_step:
                logger.error(f"[Mismatch!] Coach asked {stage} question but current_step={current_step}")
                return stage  # Return the correct stage
    
    return None  # No mismatch


# Usage in handle_conversation:
mismatch_stage = detect_stage_question_mismatch(coach_message, state["current_step"], language)
if mismatch_stage:
    logger.warning(f"[Safety Net] Auto-correcting: {state['current_step']} → {mismatch_stage}")
    internal_state["current_step"] = mismatch_stage
```

---

## 📊 **סיכום הממצאים:**

| באג | הבעיה האמיתית | הפתרון |
|-----|----------------|---------|
| א | רשימת מילים סטטית לא מזהה "רע", "חנוק" | LLM-based detection |
| ב | הפרומפט לא מזכיר רגש/מחשבה רצויים | עדכן פרומפט + הוסף לוגיקה אופציונלית |
| ג | LLM שואל שאלת S8 אבל לא מעדכן current_step | detect_stage_question_mismatch() |
| ד | בודק turns, לא תוכן דוגמאות | count_pattern_examples_in_s7() |

---

**כעת מה לעשות?**
