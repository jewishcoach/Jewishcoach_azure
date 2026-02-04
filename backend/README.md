# Jewish Coach - Backend

## 🚀 V2 is Now Default!

**V2** (Single-Agent Conversational Coach) is now the default BSD version.

### Key Features:
- ✅ **Shehiya Principle** - No rushing, stays with the user
- ✅ **14 Full Stages** (S0-S12) including Stance, Forces, Choice, Vision, Commitment
- ✅ **Built-in Gate Checks** - Automatic saturation tracking
- ✅ **Natural Language** - No rigid templates
- ✅ **Clean Language** at every stage

### Quick Comparison:

| Feature | V1 | V2 |
|---------|----|----|
| Architecture | Multi-layer | Single-agent |
| Stages | S1-S7 | S1-S12 |
| Saturation | No | Yes (0.0-1.0) |
| Gate Checks | Code-based | LLM-based |
| Language | Sometimes rigid | Always natural |

### Documentation:
- 📖 [Full Migration Guide](V2_MIGRATION_GUIDE.md)
- ⚡ [Quick Comparison](V1_VS_V2_QUICK_COMPARISON.md)

### Switch Back to V1:
```javascript
// In browser console:
window.setBsdVersion('v1')
```

Or edit `frontend/src/config.ts`:
```typescript
export const BSD_VERSION = (localStorage.getItem('bsd_version') || 'v1') as 'v1' | 'v2';
```

---

## 🧪 Testing V2

```bash
cd /home/ishai/code/Jewishcoach_azure/backend
source venv/bin/activate

# Fast simulation (S1→S5)
python test_v2_fast.py

# Advanced simulation (S5→S7)
python test_v2_advanced.py

# Full journey (S7→S12)
python test_v2_full_journey.py

# Short version (S1→S3)
python test_v2_short.py
```

---

## 🗄️ Database Reset (SQLite)

If you want to wipe local data and recreate schema (including the BSD core tables):

```bash
cd /home/ishai/code/Jewishcoach_azure/backend
./venv/bin/python scripts/reset_db.py
```

---

## 📁 Project Structure

### BSD V1 (Legacy)
- `app/bsd/router.py` - Intent routing
- `app/bsd/reasoner.py` - Content validation
- `app/bsd/conversational_coach.py` - Response generation
- `app/bsd/talker.py` - Script/natural mode
- `app/bsd/graph.py` - LangGraph orchestration

### BSD V2 (Default)
- `app/bsd_v2/single_agent_coach.py` - **Single-agent coach** (main logic)
- `app/bsd_v2/state_schema_v2.py` - State management
- `app/api/chat_v2.py` - API endpoint

---

## 🔌 API Endpoints

### V1 (Streaming)
```
POST /api/chat/conversations/{conversation_id}/messages
```

### V2 (Default)
```
POST /api/chat/v2/message
Body: {
  "message": "...",
  "conversation_id": 123,
  "language": "he"
}
```

---

## 🎯 Why V2?

1. **Shehiya (Pause) Principle** - Doesn't rush, stays with the user
2. **Automatic Gate Checks** - S3: 4 emotions, S5: full summary, S8: 2 gains + 2 losses
3. **Saturation Score** - Tracks "fullness" at each stage (0.0-1.0)
4. **Natural Language** - Multiple variations instead of fixed text
5. **14 Full Stages** - Complete BSD journey including advanced stages

---

**Last Updated:** February 3, 2026  
**Version:** V2.0 (Production)  
**Status:** 🟢 Live