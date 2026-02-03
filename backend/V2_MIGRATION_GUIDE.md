# 🚀 V2 Migration Guide

## מה השתנה?

החל מעכשיו, **V2 הוא ה-default** של המערכת!

---

## 📊 V1 vs V2 - מה ההבדל?

### **V1: Multi-Layer Architecture**
```
User Input → Router → Reasoner → Conversational Coach → Talker → Output
```

**מאפיינים:**
- ✅ מבנה מרובד עם gates קשיחים
- ✅ Router מנתח intent (ANSWER_OK, CLARIFY, etc.)
- ✅ Reasoner מאמת תוכן
- ✅ Talker בוחר בין script mode לשיחה טבעית
- ⚠️ לפעמים קשיח מדי ("זה תחום רחב! 🎯")
- ⚠️ קפיצות מהירות בין שלבים

### **V2: Single-Agent Conversational Coach**
```
User Input → Contextual Prompt → LLM → JSON Response → Output
```

**מאפיינים:**
- ✅ סוכן יחיד עם prompt עשיר
- ✅ **עקרון השהייה (Shehiya)** - לא ממהר!
- ✅ Gate Checks פנימיים (בתוך ה-LLM)
- ✅ Saturation Score אוטומטי
- ✅ שפה טבעית ומגוונת
- ✅ Clean Language בכל שלב
- ✅ 14 שלבים מלאים (S0-S12)

---

## 🔍 השוואה בדוגמאות

### דוגמה 1: S1 (נושא רחב)

**V1:**
```
User: "הורות"
Coach: "זה תחום רחב! 🎯 מה בתוך זה הכי מעניין אותך?"
```

**V2:**
```
User: "הורות"
Coach: "מה בהורות היית רוצה להתמקד בו או לחקור יותר לעומק?"
```

---

### דוגמה 2: S3 (איסוף רגשות)

**V1:**
```
Turn 1: "הרגשתי אשם"
        → "אילו עוד רגשות חווית?" (לפעמים קופץ ל-S4 מוקדם מדי)
```

**V2:**
```
Turn 1: "הרגשתי אשם"
        → "מה עוד הרגשת באותו רגע?"
Turn 2: "תסכול"
        → "מה עוד הרגשת?"
Turn 3: "כעס"
        → "מה עוד היה שם?"
Turn 4: "עצב"
        → "מה עבר לך בראש באותו רגע?" (מעבר ל-S4 רק אחרי 4 רגשות)
```

---

### דוגמה 3: S5 (סיכום המצוי)

**V1:**
```
User: "הייתי רוצה להקשיב לה באמת"
Coach: "איך היית רוצה לפעול?" → קופץ ל-S6
```

**V2:**
```
User: "הייתי רוצה להקשיב לה באמת"
Coach: "בוא נסכם את מה שקרה:
        - באותו רגע שבו ישבתם יחד
        - הרגשת אשם, תסכול, כעס ועצב
        - אמרת לעצמך 'אני בעל לא טוב'
        - והמשכת לגלול בטלפון
        - אבל היית רוצה להניח את הטלפון ולהקשיב לה באמת
        האם זה נכון?"
```

---

## 🎯 למה V2 טוב יותר?

### **1. עקרון השהייה (Shehiya)**
V2 לא ממהר! המערכת שואלת "מה עוד?" מספיק פעמים כדי לאסוף עומק אמיתי.

### **2. Gate Checks מובנים**
- S3: **חייב** 4 רגשות לפני מעבר ל-S4
- S5: **חייב** סיכום מצוי לפני מעבר ל-S6
- S8: **חייב** 2 רווחים + 2 הפסדים
- S9: **חייב** 2 ערכים + 2 יכולות

### **3. Saturation Tracking**
המערכת יודעת כמה "רווי" המשתמש בכל שלב:
- 0.25 = רק התחלנו
- 0.50 = באמצע
- 0.75 = כמעט מוכן
- 1.00 = מוכן למעבר!

### **4. שפה טבעית**
V2 משתמש בוריאציות:
- "מה עוד?"
- "מה עוד הרגשת?"
- "מה עוד היה שם?"
- "איפה עוד זה נגע בך?"

### **5. 14 שלבים מלאים**
V2 כולל את כל התהליך:
- S0: חוזה
- S1: פריקה
- S2: אירוע
- S3: רגש
- S4: מחשבה
- S5: מעשה
- S6: פער
- S7: דפוס
- **S8: עמדה (רווח/הפסד)** ← חדש!
- **S9: כוחות (מקור/טבע)** ← חדש!
- **S10: בחירה** ← חדש!
- **S11: חזון** ← חדש!
- **S12: מחויבות** ← חדש!

---

## 🔄 איך לחזור ל-V1?

אם בכל זאת תרצה לחזור ל-V1:

### **דרך 1: דרך ה-Console (זמני)**
```javascript
window.setBsdVersion('v1')
// הדף יתרענן אוטומטית
```

### **דרך 2: עריכת config (קבוע)**
ערוך את `frontend/src/config.ts`:
```typescript
export const BSD_VERSION = (localStorage.getItem('bsd_version') || 'v1') as 'v1' | 'v2';
//                                                                    ^^^ שנה ל-'v1'
```

---

## ⚙️ API Endpoints

### **V1 (Streaming)**
```
POST /api/chat/conversations/{conversation_id}/messages
```

### **V2**
```
POST /api/chat/v2/message
Body: {
  "message": "...",
  "conversation_id": 123,
  "language": "he"
}
```

---

## 📝 מה שונה בקוד?

### **V1:**
- `backend/app/bsd/router.py` - ניתוח intent
- `backend/app/bsd/reasoner.py` - אימות תוכן
- `backend/app/bsd/conversational_coach.py` - יצירת תגובה
- `backend/app/bsd/talker.py` - script mode / natural mode
- `backend/app/bsd/graph.py` - LangGraph orchestration

### **V2:**
- `backend/app/bsd_v2/single_agent_coach.py` - **הכל פה!**
- `backend/app/bsd_v2/state_schema_v2.py` - state management פשוט
- `backend/app/api/chat_v2.py` - API endpoint

---

## 🧪 בדיקות

לבדוק את V2:
```bash
cd backend
source venv/bin/activate

# סימולציה מלאה S1→S5
python test_v2_fast.py

# סימולציה מתקדמת S5→S7
python test_v2_advanced.py

# סימולציה של כל המסע S7→S12
python test_v2_full_journey.py
```

---

## 🎉 סיכום

**V2 הוא שדרוג משמעותי:**
- ✅ יותר טבעי
- ✅ יותר עומק
- ✅ יותר שהייה
- ✅ שלבים נוספים (S8-S12)
- ✅ פחות קפיצות
- ✅ Clean Language בכל שלב

**V1 עדיין זמין** אם תצטרך אותו, אבל V2 הוא העתיד! 🚀

---

## 📞 שאלות?

אם יש בעיות או שאלות:
1. בדוק את הלוגים: `backend/app/bsd_v2/single_agent_coach.py`
2. בדוק את ה-state: `collected_data`, `saturation_score`
3. חזור ל-V1 זמנית: `window.setBsdVersion('v1')`

---

**תאריך המעבר:** {{ date }}
**גרסה:** V2.0
**סטטוס:** 🟢 Production Ready
