# 🧠 Insight Analyzer - Deep Psychological Analysis

## מהו Insight Analyzer?

רכיב חדש שמספק **ניתוח פסיכולוגי עמוק** של תשובות המתאמן, ונותן **תובנות למאמן** כדי לשפר את איכות השיחה.

---

## 🎯 המטרה

**לא** לבדוק "האם עבר gate?" (זה תפקיד הRouter)  
**אלא** לענות על:
- 🔍 **איך** המתאמן עבר? (עמוק/שטחי)
- 💔 **מה** הוא משתף? (רגשות מתאימים/לא מתאימים)
- 🚨 **איפה** צריך להעמיק?
- 💡 **מה** המאמן צריך לעשות?

**חשוב:** הרכיב **לא מתערב במעבר בין שלבים** - רק משפיע על השיחה!

---

## 📊 4 סוגי ניתוח

### 1️⃣ **איכות שטחית (Shallow Engagement)**

**מה בודקים:**
- תשובות קצרות מדי (< 5 מילים)
- מילה בודדת ("כעס", "נורא")
- תשובות מתחמקות ("לא יודע", "זה מסובך")

**דוגמה:**
```
User: "כעס"
🚨 Detection: Very short response (1 word)
💡 Insight: User is being superficial - defensive or unsure
🎯 Guidance: Don't accept short answer. Ask: "ספר לי יותר על הכעס הזה"
```

---

### 2️⃣ **אי-התאמה רגשית (Emotional Incongruence)**

**מה בודקים:**
- האם הרגשות מתאימים לאירוע?
- רגשות חיוביים לאירוע שלילי = 🚨 RED FLAG

**דוגמה:**
```
Event: "אבא שלי נפטר השבוע"
User: "הרגשתי שמח, מאושר, נרגש"

🚨 Detection: Positive emotions for tragedy!
💭 Interpretation: Possible denial, avoidance, or complex feelings
🎯 Guidance: Gently probe: "שמח? זה מפתיע אותי. ספר לי יותר..."
```

---

### 3️⃣ **רגש דומיננטי (Dominant Emotion)**

**מה בודקים:**
- מה הרגש הכי חזק? (markers: "עז", "חזק", "גדול")
- מה הרגש הממוזער? (markers: "קצת", "מעט", "גם")

**דוגמה:**
```
User: "הרגשתי כעס עז, תסכול, קצת עצב"

🔍 Analysis:
  - "כעס עז" = DOMINANT (intensity marker)
  - "תסכול" = MODERATE
  - "קצת עצב" = MINIMIZED (diminisher)

💡 Insight: Anger is dominant. Sadness is minimized (defense?).
🎯 Guidance: 
  1. Focus on "כעס עז" first (strongest emotion)
  2. Then circle back: "ואת העצב? למה 'קצת'?"
```

---

### 4️⃣ **העמקה נדרשת (Unexplored Depth)**

**מה בודקים:**
- מחשבות עמוקות אבל קצרות
- vulnerable thoughts שצריכים חקירה

**דוגמה:**
```
User: "חשבתי שאני לא מספיק"
(Deep but brief - 4 words)

💡 Insight: Deep thought but unexplored
  - "לא מספיק" במה? טוב? חכם? ראוי?
🎯 Guidance: Don't rush to action. Ask:
  "לא מספיק... למה? לא מספיק טוב? חכם? מה?"
```

---

## 🏗️ איך זה עובד?

### **זרימה:**

```
1. User sends message
   ↓
2. Router validates (gate check)
   ↓
3. 🧠 Insight Analyzer runs ← NEW!
   ↓
4. Conversational Coach generates response
   (with psychological insights!)
```

### **קוד:**

```python
# In conversational_coach.py

# 1. Analyze response
analysis = await analyze_response(
    user_message=user_message,
    stage=stage,
    language=language,
    state=state
)

# 2. Log insights
logger.info(
    f"🧠 [INSIGHT ANALYSIS] Depth={analysis.depth_score:.1f}/10, "
    f"Engagement={analysis.engagement_quality.value}, "
    f"Insights={len(analysis.insights)}"
)

# 3. If high-severity insights, inject into prompt
if analysis.insights:
    for insight in analysis.insights:
        if insight.severity >= 0.6:
            # Add to system prompt:
            # "⚠️ {observation}. {suggestion}"
```

---

## 📈 מדדים שמחושבים

### **Depth Score (0-10)**

| ציון | משמעות | דוגמה |
|------|--------|-------|
| 0-2 | שטחי מאוד | "כעס" |
| 3-4 | שטחי-בינוני | "הרגשתי כעס" |
| 5-6 | בינוני | "הרגשתי כעס גדול כשהוא אמר לי..." |
| 7-8 | עמוק | "הרגשתי כעס עז כי זה העלה בי את הפחד שאני לא..." |
| 9-10 | פריצת דרך | "הבנתי שהכעס הזה בעצם מסתיר את..." |

### **Engagement Quality**

- 🟢 **DEEP**: Long, detailed, vulnerable sharing (15+ words)
- 🟡 **MODERATE**: Adequate responses (6-14 words)
- 🟠 **SHALLOW**: Short, terse, surface-level (≤5 words)
- 🔴 **AVOIDANT**: Deflecting, vague, resistant ("לא יודע")

### **Emotional Congruence**

- ✅ **CONGRUENT**: Emotions match event
- ⚠️ **INCONGRUENT**: Emotions don't match (RED FLAG!)
- ❓ **UNCLEAR**: Can't determine

---

## 🔍 דוגמאות מעשיות

### **דוגמה 1: תשובה שטחית**

```
Stage: S3 (Emotions)
User: "כעס"

🧠 Analysis:
  - Engagement: SHALLOW (1 word)
  - Depth Score: 2.0/10
  - Insight: SHALLOW_RESPONSE (severity=0.7)
    → "תשובה קצרה מאוד - אולי מתגונן"
    → "שאל: 'ספר לי יותר על הכעס הזה'"

🤖 Coach Response:
  "אני שומע - כעס. ספר לי יותר, מה בכעס הזה?"
  (Instead of accepting and moving on)
```

---

### **דוגמה 2: אי-התאמה רגשית**

```
Stage: S3 (Emotions)
Event: "אבא שלי נפטר"
User: "שמח, מאושר"

🧠 Analysis:
  - Engagement: MODERATE (2 words)
  - Emotional Congruence: INCONGRUENT (severity=0.9!)
  - Depth Score: 1.0/10 (penalty for mismatch)
  - Insight: EMOTIONAL_MISMATCH
    → "רגשות חיוביים לטרגדיה - הכחשה?"
    → "בדוק בעדינות: 'שמח? זה מפתיע אותי...'"

🤖 Coach Response:
  "אני שומע - שמח ומאושר. זה מעניין, כי אבא נפטר זה בדרך כלל 
   עצוב מאוד. ספר לי יותר על השמחה הזו..."
```

---

### **דוגמה 3: רגש דומיננטי וממוזער**

```
Stage: S3 (Emotions)
User: "הרגשתי כעס עז, תסכול, קצת עצב"

🧠 Analysis:
  - Engagement: MODERATE (6 words)
  - Depth Score: 5.0/10
  - Insight 1: DOMINANT_EMOTION
    → "כעס עז = רגש מרכזי"
    → "התמקד בכעס קודם"
  - Insight 2: MINIMIZED_EMOTION
    → "קצת עצב = ממוזער"
    → "חזור אחר כך: 'למה קצת?'"

🤖 Coach Response (First):
  "אני שומע - כעס עז, תסכול ועצב. בוא נתחיל מהכעס העז, 
   זה נשמע החזק ביותר. ספר לי על הכעס."
  
🤖 Coach Response (Later):
  "ואת העצב? שמתי לב שאמרת 'קצת'. למה קצת?"
```

---

### **דוגמה 4: מחשבה עמוקה שצריכה חקירה**

```
Stage: S4 (Thought)
User: "חשבתי שאני לא מספיק"

🧠 Analysis:
  - Engagement: SHALLOW (4 words, but vulnerable)
  - Depth Score: 6.0/10 (bonus for vulnerability)
  - Insight: UNEXPLORED_DEPTH (severity=0.8)
    → "מחשבה עמוקה אבל קצרה"
    → "אל תמהר לפעולה - שאל מה זה אומר"

🤖 Coach Response:
  "אני שומע - 'אני לא מספיק'. זו מחשבה כבדה.
   לא מספיק... במה? לא מספיק טוב? חכם? ראוי? מה בדיוק?"
  
  (Instead of immediately: "ומה עשית?")
```

---

## 🚀 שימוש

הרכיב **אוטומטי** - לא צריך לעשות כלום!

הוא רץ **אוטומטית** לפני ש-conversational_coach מייצר תשובה, ומזריק insights ישירות לפרומפט.

---

## 📊 Logging

כל ניתוח נרשם ב-logs:

```
🧠 [INSIGHT ANALYSIS] Depth=2.0/10, Engagement=shallow, Insights=1
  💡 [shallow_response] (severity=0.70): תשובה קצרה מאוד: 'כעס' (רק 1 מילים)
```

---

## 🔮 עתיד

רעיונות לשיפור:
1. **Track depth over time** - האם המתאמן מעמיק יותר עם הזמן?
2. **Pattern detection** - זיהוי דפוסים חוזרים (תמיד ממזער עצב?)
3. **Breakthrough detection** - זיהוי רגעי פריצה (Aha moments)
4. **Personalization** - התאמה לסגנון של כל מתאמן

---

## 📝 טכני

**קבצים:**
- `backend/app/bsd/insight_analyzer.py` - הרכיב עצמו
- `backend/app/bsd/conversational_coach.py` - שילוב

**Dependencies:**
- Azure OpenAI (for emotional congruence check)
- Pydantic (for data models)

**Performance:**
- Adds ~200-500ms per turn (async LLM call)
- Only high-severity insights (≥0.6) are shown to LLM

---

**Built with ❤️ to make coaching conversations more human and insightful!**

