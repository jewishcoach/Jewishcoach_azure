#!/usr/bin/env python3
"""
Full-path simulation: S0 → S13
Tests all coaching stages with realistic inputs.
"""
import sys, os, asyncio, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

os.environ["AZURE_OPENAI_DEPLOYMENT_NAME_4O_MINI"] = "gpt-4o"
os.environ["AZURE_OPENAI_API_VERSION"] = "2024-08-01-preview"
os.environ["AZURE_OPENAI_TIMEOUT_SECONDS"] = "30"
os.environ["AZURE_OPENAI_MAX_RETRIES"] = "1"
os.environ["BSD_V2_SAFETY_NET_DISABLED"] = "1"

from app.bsd_v2.single_agent_coach import handle_conversation
from app.bsd_v2.state_schema_v2 import create_initial_state

R = "\033[0m"
GR = "\033[92m"
YL = "\033[93m"
RD = "\033[91m"
CY = "\033[96m"
BL = "\033[94m"
BD = "\033[1m"

STAGE_NAMES = {
    "S0": "S0 · הסכמה",
    "S1": "S1 · נושא",
    "S2": "S2 · אירוע ספציפי",
    "S3": "S3 · רגשות",
    "S4": "S4 · מחשבה פנימית",
    "S5": "S5 · מעשה",
    "S6": "S6 · מצב רצוי",
    "S7": "S7 · פער",
    "S8": "S8 · דפוס",
    "S9": "S9 · עמדה (רווח/הפסד)",
    "S10": "S10 · כוחות וערכים",
    "S11": "S11 · בחירה",
    "S12": "S12 · חזון",
    "S13": "S13 · מחויבות",
}

# Each turn: (user_message, expected_stage_hint, comment_on_input)
SCRIPT = [
    # S0 → S1
    ("כן", "S1", "הסכמה להתאמן"),

    # S1: topic exploration
    ("הורות", "S1", "נושא כללי"),
    ("אני מתקשה להציב גבולות לילדיי", "S1", "פירוט הנושא"),
    ("אני רגיש מדי ולא אוהב עימות", "S2", "עומק הנושא → S2"),

    # S2: specific event
    ("אתמול בערב הילד שלי בן ה-10 סירב לעשות שיעורים", "S2", "התחלת אירוע"),
    ("הוא אמר לי 'לא אכפת לי' בטון מתנשא", "S2", "מה אמר"),
    ("ישבנו בסלון, אני ואשתי ושני הילדים, אחרי ארוחת ערב", "S2", "מי/מתי/איפה"),
    ("אני לא אמרתי כלום, פשוט קמתי והלכתי לחדר", "S3", "מעשה → אפשר S3"),

    # S3: emotions
    ("הרגשתי כעס גדול ואכזבה מעצמי", "S3", "רגשות אמיתיים ✓"),
    ("גם בושה שאשתי ראתה שאני לא מגיב", "S3", "עוד רגש"),
    ("תסכול וחוסר אונים", "S4", "רגשות מספיקים → S4"),

    # S4: internal thought
    ("חשבתי לעצמי: 'אני לא אבא טוב, הוא לא מכבד אותי'", "S4", "מחשבה פנימית ✓"),
    ("אמרתי לעצמי 'ויתרתי שוב, כרגיל'", "S5", "מחשבה נוספת → S5"),

    # S5: action
    ("קמתי בשקט והלכתי לחדר שינה, לא אמרתי מילה", "S5", "מעשה חיצוני ✓"),
    ("שכבתי על המיטה ובהיתי בתקרה כרבע שעה", "S6", "מעשה מלא → S6"),

    # S6: desired state
    ("הייתי רוצה להגיב בשלווה ובביטחון, להציב גבול ברור", "S6", "רצוי - פעולה"),
    ("הייתי רוצה להרגיש יציב ולא מסוחרר", "S6", "רצוי - רגש"),
    ("לחשוב 'אני אבא שמעביר מסר ברור מתוך אהבה'", "S7", "רצוי - מחשבה → S7"),

    # S7: gap (name it + score)
    ("אני אקרא לזה 'פחד מעימות'", "S7", "שם הפער ✓"),
    ("7 מתוך 10", "S8", "ציון הפער → S8"),

    # S8: pattern
    ("כן, זה קורה גם בעבודה וגם עם אשתי - בכל פעם שמישהו מתנגד לי אני נסוג", "S8", "דפוס מזוהה ✓"),
    ("תמיד: מרגיש כעס, חושב 'עדיף לשתוק', ואז יוצא מהחדר", "S9", "דפוס מלא → S9"),

    # S9: stance (gains + losses)
    ("אני מרוויח שלא יהיה ריב ואני לא צריך להתמודד עם הדחייה", "S9", "רווח ✓"),
    ("גם מרוויח תחושה שאני אדם שלום שלא מסלים", "S9", "רווח נוסף"),
    ("אני מפסיד את הכבוד של הילד ואת הסמכות שלי", "S9", "הפסד ✓"),
    ("ומפסיד את הקשר האמיתי איתו — הוא לא רואה אבא אמיתי", "S10", "הפסד נוסף → S10"),

    # S10: strengths/values
    ("ערכים? אני מאמין בכבוד הדדי ובאחריות כהורה", "S10", "ערכים ✓"),
    ("גם אמפתיה — אני מבין את הילד שלי עמוק", "S10", "ערך נוסף"),
    ("יכולת? אני יודע לדבר טוב כשאני רגוע, ואני מאד סבלני", "S11", "יכולות → S11"),

    # S11: choice
    ("אני בוחר להישאר בחדר ולהגיב מתוך שלווה — להציב גבול בלי צעקות", "S11", "בחירה ✓"),
    ("בחרתי להיות אבא שנוכח גם כשזה קשה", "S12", "בחירה מחוזקת → S12"),

    # S12: vision
    ("אני רואה שבעוד שנה הבן שלי מכבד אותי, ואנחנו מדברים בגובה עיניים", "S12", "חזון ✓"),
    ("אני מרגיש שלם עם עצמי כשאני יוצא מהשיחות האלה", "S13", "חזון מורחב → S13"),

    # S13: commitment
    ("הצעד הראשון: בפעם הבאה שהוא מסרב, אני יושב איתו שלוש דקות ואומר לו 'אני אוהב אותך וגם לא מקבל את זה'", "S13", "מחויבות קונקרטית ✓"),
]


async def run():
    print(f"\n{BD}{'='*72}{R}")
    print(f"{BD}🧪 סימולציה מלאה: S0 → S13 (שיחת הורות){R}")
    print(f"{BD}{'='*72}{R}\n")

    state = create_initial_state(
        conversation_id="full_sim_001",
        user_id="test_user",
        language="he"
    )

    stage_order = ["S0","S1","S2","S3","S4","S5","S6","S7","S8","S9","S10","S11","S12","S13"]
    prev_step = "S0"
    issues = []
    reached = set()

    for i, (user_msg, hint, comment) in enumerate(SCRIPT):
        t0 = time.time()
        try:
            coach_msg, state = await handle_conversation(user_message=user_msg, state=state)
        except Exception as e:
            print(f"{RD}❌ שגיאה בתור {i+1}: {e}{R}")
            import traceback; traceback.print_exc()
            break

        step = state.get("current_step", "?")
        sat  = float(state.get("saturation_score", 0))
        elapsed = (time.time() - t0) * 1000
        reached.add(step)

        # Detect unexpected big jumps (more than 2 stages)
        if step in stage_order and prev_step in stage_order:
            pi = stage_order.index(prev_step)
            si = stage_order.index(step)
            if si > pi + 2:
                issues.append(f"תור {i+1}: קפץ {prev_step}→{step} (דלג {si-pi-1} שלבים)")

        stage_label = STAGE_NAMES.get(step, step)
        step_color = GR if step == hint else YL
        print(f"{CY}[{i+1:02d}] 👤{R} {user_msg}")
        print(f"     {BL}💬{R} {str(coach_msg)[:120]}{'...' if len(str(coach_msg))>120 else ''}")
        print(f"     {step_color}📊 {stage_label} | sat={sat:.2f} | {elapsed:.0f}ms{R}  ← {comment}")
        print()

        prev_step = step

    # Summary
    print(f"{BD}{'='*72}{R}")
    reached_list = [s for s in stage_order if s in reached]
    not_reached  = [s for s in stage_order if s not in reached]
    print(f"\n{BD}שלבים שהגענו אליהם ({len(reached_list)}/14):{R}")
    for s in reached_list:
        print(f"  {GR}✅ {STAGE_NAMES.get(s,s)}{R}")
    if not_reached:
        print(f"\n{BD}שלבים שלא הגענו אליהם:{R}")
        for s in not_reached:
            print(f"  {YL}⏭  {STAGE_NAMES.get(s,s)}{R}")
    if issues:
        print(f"\n{BD}בעיות שנמצאו:{R}")
        for iss in issues:
            print(f"  {RD}⚠️  {iss}{R}")
    else:
        print(f"\n{GR}{BD}✅ לא נמצאו קפיצות חריגות!{R}")
    print(f"{BD}{'='*72}{R}\n")


if __name__ == "__main__":
    asyncio.run(run())
