# Situation Validation - 4 Required Criteria (S2)

## Overview

This document describes the 4 mandatory criteria that every situation must meet before progressing from S2 (Event) to S3 (Emotions).

The validation is performed by the `validate_situation_quality()` function using LLM-based detection.

---

## 🎯 The 4 Required Criteria

### 1️⃣ Appropriate Time Frame
**Definition:** The event happened recently - between 2 weeks to 2 months ago.

**Why:** The memory is still fresh but the user has gained some distance.

**If missing:**
```
כדי שנוכל לעבוד בצורה מדויקת, חשוב שניקח אירוע שהזיכרון שלו עדיין טרי, אבל הספקת מעט להתרחק ממנו. 
תוכל להביא סיטואציה שקרתה בטווח של השבועיים עד החודשיים האחרונים?

חשוב לי להדגיש: הסיטואציה לא חייבת להיות קשורה לנושא האימון. 
הדפוס שלנו הולך איתנו לכל מקום, ולפעמים דווקא באירוע מתחום אחר לגמרי הוא מתגלה בצורה הכי נקייה וברורה.
```

---

### 2️⃣ Personal Involvement
**Definition:** The user acted or reacted in the event - they weren't just a passive observer.

**Why:** We need to see the user's pattern of response, not others' behavior.

**If missing:**
```
אני מבין את הסיטואציה שתיארת. 
בשלב זה אנחנו מחפשים אירוע שבו אתה הגבת ופעלת. 
תוכל לחשוב על אירוע כזה?
```

**Examples:**
- ✅ "I spoke up in the meeting"
- ✅ "I responded angrily"
- ❌ "I watched my son play" (passive)
- ❌ "My boss yelled at someone" (not about the user)

---

### 3️⃣ Emotional Signature (Turmoil & Storm)
**Definition:** The event touched the user, stirred them up, caused emotional turmoil.

**Why:** A "dry" or technical event won't reveal deep patterns.

**If missing:**
```
תיארת את השתלשלות העניינים, אבל כדי לזהות דפוס אנחנו מחפשים אירוע שבו זה פגש אותך באופן שגרם לך לטלטלה, לסערה. 
תוכל לתת לי אירוע שבו ההתרחשות כל כך נגעה בך עד שהיית נסער?
```

**Examples:**
- ✅ "I felt crushed and humiliated"
- ✅ "It shook me, I was in turmoil"
- ❌ "It was fine, nothing special"
- ❌ "I handled it professionally" (too technical)

---

### 4️⃣ Interpersonal Arena
**Definition:** Other people were involved besides the user - it can't be the user alone with themselves.

**Why:** Patterns emerge in relationships and interactions with others.

**If missing:**
```
אני מבין את החוויה שתיארת, אבל כדי לזהות דפוס אנחנו מחפשים אירוע שהיו מעורבים בו אנשים נוספים מלבדיך. 
תוכל לחשוב על אירוע כזה, שבו הייתה התרחשות או אינטראקציה בינך לבין אחרים?
```

**Examples:**
- ✅ "Conversation with my spouse"
- ✅ "Meeting with my boss"
- ✅ "Argument with my kids"
- ❌ "I thought about my career" (internal process)
- ❌ "I read an article that upset me" (no interpersonal interaction)

---

## 🛠️ Technical Implementation

### Function: `validate_situation_quality()`

**Location:** `backend/app/bsd_v2/single_agent_coach.py`

**Input:**
- `state`: Current conversation state
- `llm`: Language model instance
- `language`: "he" or "en"

**Output:**
- `(True, None)`: All criteria met, proceed to S3
- `(False, guidance_message)`: Criteria not met, show guidance and stay in S2

**How it works:**
1. Extracts last 5 user messages from S2
2. Calls LLM with validation prompt
3. LLM returns JSON with 4 boolean flags
4. If any flag is False, returns the appropriate guidance message
5. If all flags are True, allows progression to S3

**Usage:**
The function is called in `handle_conversation()` before `validate_stage_transition()`:

```python
if old_step == "S2" and new_step == "S3":
    situation_valid, guidance = await validate_situation_quality(state, llm, language)
    if not situation_valid and guidance:
        logger.warning(f"[Safety Net] Situation doesn't meet criteria, blocking S2→S3")
        coach_message = guidance
        internal_state["current_step"] = "S2"  # Stay in S2
```

---

## 📊 Validation Flow

```
User in S2 → Describes situation
      ↓
LLM wants to move to S3
      ↓
Safety Net: validate_situation_quality()
      ↓
   Check 4 criteria
      ↓
   ┌─────────────┐
   │ All 4 met?  │
   └─────┬───────┘
         │
    ┌────┴────┐
   Yes       No
    │         │
    │    Return guidance
    │    Stay in S2
    │         │
    ↓         ↓
Progress   Ask for
 to S3    new event
```

---

## 🎯 Examples

### ✅ Good Situation (All 4 criteria)
```
User: "לפני שבועיים היה לי ויכוח עם הבוס שלי על הפרויקט. 
       הוא ביקר אותי בפגישה מול כולם ואני הרגשתי ממש פגוע.
       ניסיתי להסביר את עצמי אבל לא יצא לי."

✓ Time: 2 weeks ago
✓ Personal: User tried to explain
✓ Emotional: Felt hurt
✓ Interpersonal: Boss and team present

→ Proceed to S3
```

### ❌ Bad Situation (Missing criteria)
```
User: "חשבתי הרבה על הקריירה שלי בשנה האחרונה.
       אני מרגיש שאני לא מתקדם מספיק."

✗ Time: "Last year" - too far back
✗ Personal: "Thought" - internal process
✗ Emotional: Generic feeling
✗ Interpersonal: No other people

→ Ask for new event with guidance
```

---

## 🔄 Integration with Other Safety Nets

This validation works **alongside** existing safety nets:
- **detect_stuck_loop()**: Prevents repeating questions
- **has_sufficient_event_details()**: Checks for enough detail
- **validate_stage_transition()**: General stage transition rules

**Order of execution:**
1. `validate_situation_quality()` ← New (4 criteria)
2. `validate_stage_transition()` (turns, details, etc.)

---

## 📝 Prompt Updates

The prompt was updated to instruct the LLM about these criteria:

### Hebrew (lines ~92-148):
```markdown
**🚨 CRITICAL - 4 תנאים חובה לסיטואציה (S2):**

כדי שסיטואציה תאושר למעבר ל-S3, היא חייבת לעמוד ב-**כל 4 התנאים**:
1. מסגרת זמן מתאימה
2. מעורבות אישית ואקטיבית
3. חתימה רגשית (טלטלה וסערה)
4. זירה בין-אישית
```

### English (lines ~652-707):
```markdown
**🚨 CRITICAL - 4 Required Criteria for Situation (S2):**

For a situation to be approved for S3 transition, it MUST meet **all 4 criteria**:
1. Appropriate Time Frame
2. Personal Involvement
3. Emotional Signature (turmoil and storm)
4. Interpersonal Arena
```

---

## 🚀 Expected Impact

**Before:**
- Coach moved to S3 too quickly
- Worked with weak/irrelevant situations
- Pattern identification was shallow

**After:**
- Only strong, relevant situations proceed to S3
- Clear guidance when criteria aren't met
- Deeper pattern work with quality situations
- User understands why we need a different event

---

## 📚 Related Files

- `backend/app/bsd_v2/single_agent_coach.py` - Implementation
- `backend/app/bsd_v2/prompt_compact.py` - LLM instructions
- `SITUATION_VALIDATION.md` - This documentation
