# Dynamic Opener Generator - Anti-Robotics System

## Problem

**Before:** Coach responses felt robotic due to repetitive openers:
- "שמעתי אותך." (every time)
- "I hear you." (every time)
- Generic, predictable, not contextual

## Solution

**LLM-generated openers with hard rules:**

```python
opener_result = await generate_opener(
    user_message="ביקשתי מהילדה לשטוף כלים והיא סירבה",
    language="he",
    stage="S2",
    is_advance=False,
    critique="User provided event",
    recent_openers=state.recent_openers
)

# Returns:
# OpenerResult(
#     use_opener=True,
#     opener="ביקשת מהילדה לשטוף כלים והיא סירבה.",
#     style_tag="reflective"
# )
```

## Architecture

### 1. LLM Generation (Layer 1)
- Generates short, natural opener (0-12 words)
- Context-aware (stage, user message, critique)
- Can decide NOT to use opener (especially for advance)

### 2. Hard Rules (Layer 2)
Enforces quality after LLM:

| Rule | Enforcement |
|------|-------------|
| **Max length** | 12 words max (truncates if longer) |
| **No repetition** | Checks last 3-5 openers, disables if >60% overlap |
| **No interpretation** | Blocks "נראה ש", "אני חושב", "זה אומר" |
| **Not mandatory** | Advance often skips opener (cleaner flow) |

## Integration

### State Schema
```python
class BsdState(BaseModel):
    recent_openers: List[str] = Field(default_factory=list)
```

### Talker
```python
async def generate_coach_message(..., recent_openers: list[str] = None) -> tuple[str, str | None]:
    # Returns (message, opener_used)
```

### Graph
```python
coach_message, opener_used = await generate_coach_message(...)

if opener_used:
    state.recent_openers.append(opener_used)
    if len(state.recent_openers) > 5:
        state.recent_openers = state.recent_openers[-5:]
```

## Examples

### Loop (needs opener)
```
User: "כעס"
Opener: "אני שומע: כעס."
Script: "איזה עוד רגש היה שם?"
```

### Advance (often no opener)
```
User: "כעס, בושה, קנאה, תסכול"
Opener: (none)
Script: "מעולה. עכשיו נפריד את החוויה לשלושה מסכים..."
```

### Contextual reflection
```
User: "ביקשתי מהילדה לשטוף כלים והיא סירבה"
Opener: "ביקשת מהילדה לשטוף כלים והיא סירבה."
Script: "עכשיו נפריד את החוויה..."
```

## Key Principles

1. **LLM generates, rules enforce** - Best of both worlds
2. **Varied, not random** - Context-aware but controlled
3. **Not always needed** - Advance often cleaner without opener
4. **Anti-repetition** - Tracks recent openers, blocks similar ones
5. **Reflection-only** - No interpretation, no commentary

## Testing

```bash
cd backend
python3 << 'EOF'
from app.bsd.opener_generator import generate_opener
import asyncio

result = asyncio.run(generate_opener(
    user_message="כעס, בושה",
    language="he",
    stage="S3",
    is_advance=False,
    critique="Need more emotions",
    recent_openers=[]
))

print(f"Use opener: {result.use_opener}")
print(f"Opener: {result.opener}")
EOF
```

## Files

- `opener_generator.py` - Core logic
- `state_schema.py` - Added `recent_openers: List[str]`
- `talker.py` - Returns `(message, opener)` tuple
- `graph.py` - Tracks openers in state
- `tests/test_opener_generator.py` - Unit tests

## Benefits

✅ **Natural** - Contextual, varied responses  
✅ **Controlled** - Hard rules prevent bad output  
✅ **Efficient** - LLM only for opener, not full message  
✅ **Testable** - Rules are deterministic  
✅ **Scalable** - Works for all 11 stages


## S3 Special Rule: Emotion List Only

### Problem
In S3 (Emotion Screen), the coach was generating long sentences instead of listing emotions:

❌ BAD:
```
בעצמי עליה שהיא מסיעה לפמוש את אמא שלה כי הרגשותי שלה לא עושה את זה בשביל אמא שלה...
```

✅ GOOD:
```
אני שומע: כעס, בושה.
```

### Solution
Added **S3-specific validation** to `opener_generator.py`:

1. **LLM Prompt**: Special system message for S3 that explicitly requires emotion list format
2. **Hard Rule**: `_is_emotion_list_format()` checks that opener starts with:
   - Hebrew: "אני שומע:" or "שמעתי:"
   - English: "I hear:" or "I heard:"
3. **Enforcement**: If S3 opener doesn't match format → disabled (better no opener than wrong format)

### Code
```python
def _is_emotion_list_format(text: str, language: str) -> bool:
    """Check if text follows emotion list format."""
    text_lower = text.lower().strip()
    
    if language == "he":
        return text_lower.startswith("אני שומע:") or text_lower.startswith("שמעתי:")
    else:
        return text_lower.startswith("i hear:") or text_lower.startswith("i heard:")
```

### Examples

**Valid S3 openers:**
- "אני שומע: כעס, בושה, קנאה."
- "I hear: anger, shame, jealousy."

**Invalid (will be disabled):**
- "בעצמי עליה שהיא מסיעה..." (sentence)
- "הבנתי. ביקשת מהילדה..." (full sentence)
- "You asked your daughter..." (full sentence)

### Result
✅ S3 now **only** shows emotion lists, never long sentences  
✅ If LLM fails to generate correct format → no opener (safe fallback)  
✅ Maintains clean, focused emotion screen experience


