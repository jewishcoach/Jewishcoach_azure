# Quick Test: Enterprise Loop Handling 🧪

## Test the S3 Accumulation Fix

### Expected Behavior

**Turn 1: User gives 3 emotions**
```
User: "כעס, תסכול, יאוש"

Expected Response:
"שמעתי: כעס, תסכול, יאוש.

חסר עוד 1 רגש. איזה עוד רגש היה שם?"
```

**Turn 2: User gives 1 more emotion**
```
User: "עצבנות"

Expected Response:
"מעולה.

מאחורי הרגש יש בדרך כלל משפט פנימי.
מה הייתה המחשבה המילולית שעברה בך באותו רגע? משפט אחד."

[System advanced to S4! ✅]
```

---

## What Changed

### Before (BROKEN ❌)
- User: "כעס, תסכול, יאוש" (3 emotions)
- System: LOOP - "אילו רגשות התעוררו בך?" (full script again)
- User: "עצבנות" (1 emotion)
- System: LOOP - "אילו רגשות התעוררו בך?" (STUCK FOREVER!)

**Problem:** System counted only the CURRENT message, not accumulated emotions.

### After (FIXED ✅)
- User: "כעס, תסכול, יאוש" (3 emotions)
- System: LOOP - "חסר עוד 1 רגש" (short, focused)
- User: "עצבנות" (1 emotion)
- System: ADVANCE to S4! (total 4 emotions accumulated)

**Solution:** 
1. ✅ Accumulation across loops
2. ✅ Short loop prompts (not full script)
3. ✅ Input validation (rejects numbers)

---

## Test Steps

1. **Open the frontend** (http://localhost:5174)
2. **Start a new conversation**
3. **Progress to S3:**
   - S0: "כן" (consent)
   - S1: "הורות" (topic)
   - S2: "ביקשתי מהילדה לשטוף כלים והיא סירבה" (event)
4. **Test accumulation at S3:**
   - Send: "כעס, תסכול, יאוש" (3 emotions)
   - **Verify:** System says "חסר עוד 1 רגש" (NOT the full script!)
   - Send: "עצבנות" (1 more emotion)
   - **Verify:** System advances to S4 (thought screen)
5. **Test invalid input:**
   - If you send "1,2,3,4" at S3
   - **Verify:** System says "אני רואה מספרים..."

---

## Check Logs

Watch the backend logs to see the accumulation:

```bash
tail -f terminals/40.txt | grep -E "REASONER|TALKER|Advancing|Looping"
```

Expected output:
```
🔁 [REASONER S3] LOOP - accumulated 3 emotions: ['כעס', 'תסכול', 'יאוש']. Need 1 more.
🗣️ [TALKER S3] Using LOOP PROMPT (short, focused)
🔁 Looping in S3 (loop #1)

✅ [REASONER S3] ADVANCE - accumulated 4 emotions: ['כעס', 'תסכול', 'יאוש', 'עצבנות']
🗣️ [TALKER S4] Using FULL SCRIPT (advance)
✅ Advancing: S3 → S4
```

---

## Database Verification

Check that emotions are persisted:

```bash
cd backend
./venv/bin/python -c "
from app.database import SessionLocal
from app.models import BsdSessionState

db = SessionLocal()
state = db.query(BsdSessionState).order_by(BsdSessionState.id.desc()).first()
if state:
    print(f'Stage: {state.current_stage}')
    print(f'Emotions: {state.cognitive_data.get(\"event_actual\", {}).get(\"emotions_list\", [])}')
    print(f'Metrics: {state.metrics}')
db.close()
"
```

Expected output:
```
Stage: S4
Emotions: ['כעס', 'תסכול', 'יאוש', 'עצבנות']
Metrics: {'loop_count_in_current_stage': 0, 'shehiya_depth_score': 0.0}
```

---

## Success Criteria

✅ System accumulates emotions across loops  
✅ System uses short loop prompts (not full script)  
✅ System advances after 4 emotions accumulated  
✅ System validates input (rejects numbers)  
✅ Emotions persist in database  
✅ Logs show accumulation logic working  

---

## Troubleshooting

### System still stuck in loop?
- Check logs for "REASONER S3" to see accumulated count
- Verify `cognitive_data` is being passed to `decide()`
- Check DB: `cognitive_data.event_actual.emotions_list`

### System still using full script on loop?
- Check logs for "TALKER S3" - should say "Using LOOP PROMPT"
- Verify `is_loop=True` is being passed to `generate_coach_message()`

### Numbers accepted as emotions?
- Check logs for "Invalid input detected"
- Verify `_detect_invalid_input()` is being called

---

**Ready to test!** 🚀

Open the frontend and try the flow above. The system should now handle loops gracefully and accumulate data properly.



