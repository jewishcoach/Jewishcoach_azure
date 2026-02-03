# Smart Insights Upgrade 🧠✨

## What We Built

Upgraded the Insights Widget from **simple polling** to **smart draft/final modes**, combining:
- ✅ **Enterprise BSD logic** (new: LangGraph, Reasoner/Talker, Accumulation)
- ✅ **Smart UI widgets** (old: ReflectionCard, GapWidget, PatternWidget)

**Result:** Best of both worlds! 🎉

---

## Architecture

### Backend: Widget Mapper Layer

**New File:** `backend/app/bsd/widget_mapper.py`

Maps BSD cognitive data to frontend widget format:

```python
def stage_to_widget_name(stage_id: str) -> str:
    """S3 → 'Emotions', S6 → 'Gap', S9 → 'KaMaZ'"""

def get_stage_title(stage_id: str, language: str) -> str:
    """S3 → 'מסך הרגש' (he) or 'Emotion Screen' (en)"""

def extract_widget_data(cognitive_data: CognitiveData, stage_id: str) -> Dict:
    """Extract stage-specific data for widgets"""

def should_show_widget(stage_id: str, cognitive_data: CognitiveData) -> bool:
    """Check if stage has enough data to display"""
```

**Integration:** `backend/app/bsd/engine.py`

```python
# In run_turn(), after persisting data:

widget_data = None
if should_show_widget(db_state.current_stage, cd_model):
    widget_data = {
        "type": "reflection",
        "status": "draft" if decision == "loop" else "final",  # ← KEY!
        "stage": stage_to_widget_name(db_state.current_stage),
        "title_he": get_stage_title(db_state.current_stage, "he"),
        "title_en": get_stage_title(db_state.current_stage, "en"),
        "data": extract_widget_data(cd_model, db_state.current_stage)
    }

metadata["tool_call"] = widget_data  # ← Sent in SSE stream
```

---

### Frontend: Smart Insights Panel

**New File:** `frontend/src/components/InsightHub/SmartInsightsPanel.tsx`

Replaces the simple `InsightsPanel` with smart draft/final display:

```tsx
// Polls /insights every 3 seconds
const insights = await apiClient.getConversationInsights(conversationId);

// Determines draft/final based on current phase
const status = currentPhase === 'S3' ? 'draft' : 'final';

// Uses ReflectionCard from old system
<ReflectionCard status={status} title="מסך הרגש">
  <EmotionsWidget data={insights.event_actual.emotions_list} />
</ReflectionCard>
```

**Reused Components:**
- ✅ `ReflectionCard` - Draft/final visual states
- ✅ `GapWidget` - Current → Gap → Desired
- ✅ `PatternWidget` - Trigger → Reaction → Consequence
- ✅ `ListWidget` - Pain points, gains/losses, beliefs

---

## Draft vs Final Logic

### Backend Decision (in `engine.py`):

```python
decision = await reasoner.decide(...)

if decision == "loop":
    status = "draft"  # Still collecting data in this stage
else:  # decision == "advance"
    status = "final"  # Stage completed, moving to next
```

### Frontend Display:

**Draft Mode** (current stage, still looping):
```
┌─ ⏰ מתגבש ─────────────────┐
│ מסך הרגש                   │
│ [כעס] [קנאה] [תסכול]       │
│ (חסר עוד 1 רגש...)         │
└─ border-dashed, orange ────┘
```

**Final Mode** (stage completed):
```
┌─ ✓ נקלט ──────────────────┐
│ מסך הרגש                   │
│ [כעס] [קנאה] [תסכול] [יאוש]│
│                             │
└─ border-solid, green + glow┘
```

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. User sends message                                        │
│    → Backend: BsdEngine.run_turn()                           │
│    → Reasoner decides: loop or advance                       │
│    → Talker generates response                               │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. Engine builds widget_data                                 │
│    → widget_mapper.extract_widget_data()                     │
│    → status = "draft" if loop else "final"                   │
│    → Adds to metadata["tool_call"]                           │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. SSE stream sends metadata to frontend                     │
│    → Frontend receives tool_call (optional, for future)      │
│    → For now: polling /insights every 3 seconds              │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. SmartInsightsPanel renders                                │
│    → Fetches cognitive_data from /insights                   │
│    → Determines draft/final based on currentPhase            │
│    → Uses ReflectionCard + appropriate widget                │
└──────────────────────────────────────────────────────────────┘
```

---

## Stage-Specific Widgets

| Stage | Widget | Data | Display |
|-------|--------|------|---------|
| S1 | Simple text | `topic` | Plain text |
| S3 | Emotion pills | `emotions_list` | Colored pills with animation |
| S4 | Quoted text | `thought_content` | Italic quote |
| S5 | Plain text | `action_content` | Description |
| S6 | **GapWidget** | `current_reality`, `desired_reality` | Current → Arrow → Desired |
| S7 | **PatternWidget** | `trigger`, `reaction`, `consequence` | 3-step flow |
| S8 | Simple text | `identity` | Bold text |
| S9 | Two lists | `source_forces`, `nature_forces` | Blue pills (source) + Green pills (nature) |
| S10 | Key-value | `difficulty`, `result` | Structured display |

---

## Example: S3 (Emotions) Flow

### Turn 1: User gives 2 emotions

**User:** "כעס, קנאה"

**Backend:**
```python
# Reasoner
emotions = ["כעס", "קנאה"]
count = 2 < 4 → decision = "loop"

# Engine
widget_data = {
    "status": "draft",  # ← Still looping!
    "stage": "Emotions",
    "data": {"emotions_list": ["כעס", "קנאה"]}
}
```

**Frontend:**
```tsx
<ReflectionCard status="draft" title="מסך הרגש">
  {/* Orange border, dashed, clock icon */}
  <span>כעס</span>
  <span>קנאה</span>
  {/* Shows "מתגבש" badge */}
</ReflectionCard>
```

### Turn 2: User gives 2 more emotions

**User:** "תסכול יאוש"

**Backend:**
```python
# Reasoner (with accumulation!)
existing = ["כעס", "קנאה"]
new = ["תסכול", "יאוש"]
merged = ["כעס", "קנאה", "תסכול", "יאוש"]
count = 4 >= 4 → decision = "advance"

# Engine
widget_data = {
    "status": "final",  # ← Stage completed!
    "stage": "Emotions",
    "data": {"emotions_list": ["כעס", "קנאה", "תסכול", "יאוש"]}
}
```

**Frontend:**
```tsx
<ReflectionCard status="final" title="מסך הרגש">
  {/* Green border, solid, checkmark icon, glow animation */}
  <span>כעס</span>
  <span>קנאה</span>
  <span>תסכול</span>
  <span>יאוש</span>
  {/* Shows "נקלט" badge */}
</ReflectionCard>
```

---

## Files Changed

### Backend

| File | Changes | Lines |
|------|---------|-------|
| `backend/app/bsd/widget_mapper.py` | New module for data mapping | +200 |
| `backend/app/bsd/engine.py` | Add widget_data to metadata | +15 |

**Total Backend:** ~215 lines

### Frontend

| File | Changes | Lines |
|------|---------|-------|
| `frontend/src/components/InsightHub/SmartInsightsPanel.tsx` | New smart panel | +350 |
| `frontend/src/components/InsightHub/InsightHub.tsx` | Use SmartInsightsPanel | +2 |

**Total Frontend:** ~352 lines

**Grand Total:** ~567 lines

---

## What's Different from Old System?

### Old System (backup):
- ❌ Used old supervisor logic (not BSD core)
- ❌ Tool_call sent in SSE stream
- ❌ ActiveToolRenderer as primary display
- ✅ Had draft/final modes
- ✅ Had smart widgets

### New System (now):
- ✅ Uses enterprise BSD core (LangGraph + Reasoner/Talker)
- ✅ Tool_call available in metadata (for future SSE)
- ✅ SmartInsightsPanel as primary display
- ✅ Has draft/final modes
- ✅ Has smart widgets
- ✅ **Accumulation across loops**
- ✅ **Constitutional guardrails**
- ✅ **Loop prompts**

**Result:** Enterprise backend + Smart UI = Best of both! 🎉

---

## Testing

### 1. Backend: Widget Mapper

```bash
cd backend
./venv/bin/python -c "
from app.bsd.widget_mapper import *
print(stage_to_widget_name('S3'))  # → 'Emotions'
print(get_stage_title('S3', 'he'))  # → 'מסך הרגש'
"
```

### 2. Frontend: Draft/Final Display

1. **Start new conversation**
2. **Progress to S3:**
   - S0: "כן"
   - S1: "הורות"
   - S2: "ביקשתי מהילדה לשטוף כלים"
3. **Test draft mode:**
   - Send: "כעס, קנאה" (2 emotions)
   - **Verify:** Orange dashed border, "מתגבש" badge, clock icon
4. **Test final mode:**
   - Send: "תסכול יאוש" (2 more emotions)
   - **Verify:** Green solid border, "נקלט" badge, checkmark icon, glow animation
5. **Check persistence:**
   - Refresh page
   - **Verify:** S3 card still shows as "final" with all 4 emotions

---

## Future Enhancements

### 1. Real-time SSE Updates (instead of polling)

Currently: Polling `/insights` every 3 seconds

**Future:** Use `tool_call` from SSE stream:

```tsx
// In useChat.ts
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.tool_call) {
    // Update insights immediately
    setCurrentInsight(data.tool_call);
  }
};
```

### 2. Transition Animations

When status changes from draft → final:

```tsx
<motion.div
  animate={{ 
    scale: [1, 1.05, 1],
    borderColor: ['#fb923c', '#22c55e']
  }}
  transition={{ duration: 0.8 }}
>
  <ReflectionCard status="final" />
</motion.div>
```

### 3. Progress Indicators

Show progress within draft mode:

```tsx
{status === 'draft' && (
  <div className="mt-2 text-xs text-orange-600">
    {emotions.length}/4 רגשות נאספו
  </div>
)}
```

### 4. Edit Mode

Allow editing insights in final mode:

```tsx
<ReflectionCard 
  status="final"
  editable
  onEdit={(newData) => updateInsight(stage, newData)}
/>
```

---

## Summary

| Feature | Old System | New System |
|---------|------------|------------|
| Backend Logic | Old supervisor | ✅ Enterprise BSD (LangGraph) |
| Accumulation | ❌ No | ✅ Yes (emotions across loops) |
| Draft/Final UI | ✅ Yes | ✅ Yes |
| Smart Widgets | ✅ Yes | ✅ Yes |
| Loop Prompts | ❌ No | ✅ Yes (short, focused) |
| Constitutional Guards | ❌ No | ✅ Yes (zero interpretations) |
| Data Source | SSE stream | Polling (SSE ready) |

---

**Status:** ✅ Complete & Tested  
**Next:** Test with real users and monitor UX feedback

**The system now has:**
- 🧠 **Smart backend** - Enterprise BSD logic
- ✨ **Smart UI** - Draft/final visual feedback
- 🔄 **Accumulation** - Data persists across loops
- 🎯 **Best of both worlds!**



