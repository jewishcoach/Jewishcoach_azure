"""
Pedagogical station checkpoints between BSD floors (V2).

Rules (product):
- Offer a full station wrap (summary tone + homework + praise + permission to continue)
  only when the coach advances into a milestone step AND at least 10 minutes have passed
  since max(training_started_at, last_station_checkpoint_at).
- Persist active homework in v2_state for Insights + sticky UI.
- Session-flow flags for pause vs immediate continue drive the *next* user-coach turn opening.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Steps that mark entering a new "floor" after substantive work (aligned with V2 S7–S15).
STATION_ENTRY_STEPS: frozenset[str] = frozenset(
    {"S7", "S8", "S9", "S10", "S11", "S12", "S13", "S14", "S15"}
)

MINUTES_BETWEEN_ANCHORS = 10


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    try:
        # Python 3.11+ handles "Z"
        t = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def ensure_training_started_at(state: Dict[str, Any]) -> None:
    """Call before the first user turn is processed — starts the 10-minute training clock."""
    if state.get("training_started_at"):
        return
    msgs = state.get("messages") or []
    user_count = sum(1 for m in msgs if isinstance(m, dict) and m.get("sender") == "user")
    if user_count == 0:
        state["training_started_at"] = _utc_now().isoformat()


def station_time_anchor_eligible(state: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """True if ≥ MINUTES_BETWEEN_ANCHORS since max(training_started_at, last_station_checkpoint_at)."""
    now = now or _utc_now()
    t0 = _parse_iso(state.get("training_started_at")) or now
    last_cp = _parse_iso(state.get("last_station_checkpoint_at"))
    anchor = max(t0, last_cp) if last_cp else t0
    delta_sec = (now - anchor).total_seconds()
    return delta_sec >= MINUTES_BETWEEN_ANCHORS * 60


def _already_offered_for_step(state: Dict[str, Any], step: str) -> bool:
    offered: List[str] = state.setdefault("stations_offered_steps", [])
    return step in offered


def _mark_offered(state: Dict[str, Any], step: str) -> None:
    offered: List[str] = state.setdefault("stations_offered_steps", [])
    if step not in offered:
        offered.append(step)


def _fallback_homework(step: str, language: str) -> Tuple[str, str]:
    """Short default mission if the model omits structured shehiya fields."""
    if language == "en":
        titles = {s: "Between sessions" for s in STATION_ENTRY_STEPS}
        bodies = {
            "S7": "Notice 1–2 moments this week where the gap shows up; jot a line each time in the app journal.",
            "S8": "Watch for the pattern “on a hot plate” — name it quietly when it appears, without forcing change.",
            "S9": "When the paradigm appears in real life, simply notice: “here it is.”",
            "S10": "Once, observe the price your old stance takes in a daily situation.",
            "S11": "Side-glance: what does the stance cost you in one concrete moment?",
            "S12": "Live with one source trait from your card each morning; feel how it lights something in you.",
            "S13": "Rehearse the new stance sentence + one short guided imagination of acting from the new mix.",
            "S14": "Stay a moment with what you are willing to release; hold the question gently.",
            "S15": "Take one measurable step toward your commitment; note outcome in the journal.",
        }
        default_body = "Short note in the journal about what you noticed."
    else:
        titles = {s: "משימת השהיה" for s in STATION_ENTRY_STEPS}
        bodies = {
            "S7": "שימו לב השבוע ל־1–2 רגעים שבהם הפער מופיע; כתבו משפט קצר ביומן באפליקציה.",
            "S8": "«תפיסה על חם»: כשהדפוס מופיע — רק לצפות, בלי לכפות שינוי. אפשר להגיד לעצמכם: «הנה זה קורה».",
            "S9": "כשהפרדיגמה מופיעה במציאות — רק להבחין בה, בלי מאבק.",
            "S10": "«מבט מהצד»: פעם אחת השבוע — מה העמדה הישנה גובה מכם ברגע קונקרטי.",
            "S11": "להתבונן במחיר שהעמדה גובה מאירוע יומיומי אחד.",
            "S12": "לבחור בכל בוקר תכונת מקור אחת מהכמ״ז ולהרגיש איך היא «מאירה» במהלך היום.",
            "S13": "לשנן משפט עמדה חדש ולדמיין קצר פעולה אחת לפי התמהיל.",
            "S14": "להישאר רגע עם נקודת הוויתור — בשאלה עדינה: האם אני באמת מוכן לשחרר?",
            "S15": "צעד מדיד אחד לקראת המחויבות; לתעד בתוצאה ביומן.",
        }
        default_body = "תיעוד קצר באפליקציה של מה ששמתם לב בינתיים."
    return titles.get(step, "משימה" if language != "en" else "Homework"), bodies.get(step, default_body)


def station_title_for_step(step: str, language: str) -> str:
    if language == "en":
        names = {
            "S7": "Gap floor",
            "S8": "Pattern",
            "S9": "Paradigm",
            "S10": "Stance & trigger",
            "S11": "Gains & losses",
            "S12": "KaMaZ forces",
            "S13": "Renewal & choice",
            "S14": "Vision",
            "S15": "Commitment",
        }
        return names.get(step, "Station")
    names = {
        "S7": "ניתוח הפער",
        "S8": "דפוס",
        "S9": "פרדיגמה",
        "S10": "עמדה וטריגר",
        "S11": "רווח והפסד",
        "S12": "כמ״ז",
        "S13": "התחדשות ובחירה",
        "S14": "חזון",
        "S15": "מחויבות",
    }
    return names.get(step, "תחנה")


def build_session_flow_prompt_addon(state: Dict[str, Any], language: str) -> str:
    """Inject after base system prompt — consumed flags cleared after the coach turn (caller)."""
    sf = state.get("session_flow") or {}
    blocks: List[str] = []

    if sf.get("paused_at_station"):
        if language == "he":
            blocks.append(
                "\n\n# הקשר מיוחד לתור זה\n"
                "המתאמן/ת **חזר/ה אחרי עצירה** בנקודת תחנה (בחר/ה לעצור לאחר משימת השהיה).\n"
                "**חובה:** פתחו בניסוח **חי וקצר** שמקבל את החזרה (לא נוסח קבוע שחוזר על עצמו מדי פעם).\n"
                "אחר כך שאלו **בעדינות** איך הלך עם **משימת ההשהיה** — נסחו אחרת מפעם לפעם; אל תשכפלו משפט זהה בכל שיחה.\n"
                "אם אין רצון לפרט — קבלו ותמשיכו בלי ללחוץ.\n"
                "אל תציינו שזה «מערכת» או «בוט»."
            )
        else:
            blocks.append(
                "\n\n# Special context for this turn\n"
                "The coachee **returned after pausing** at a station checkpoint.\n"
                "Open with a **fresh, short** welcome-back (avoid the same scripted line every time).\n"
                "Then **gently** ask how the between-session homework went — vary wording; don't repeat an identical sentence each session.\n"
                "If they don't want to elaborate, accept and move on.\n"
                "Do not mention 'system' or 'bot'."
            )

    if sf.get("continued_immediately_next"):
        if language == "he":
            blocks.append(
                "\n\n# הקשר מיוחד לתור זה\n"
                "המתאמן/ת **בחר/ה להמשיך באימון** מיד אחרי נקודת התחנה (ללא עצירה מוצהרת).\n"
                "שאלו **מינימום** על המשימה — משפט אחד קצר או שילוב בשאלה הבאה — ואל תאריכו חקירה ארוכה.\n"
                "המשיכו לעומק השלב."
            )
        else:
            blocks.append(
                "\n\n# Special context for this turn\n"
                "The coachee **chose to continue coaching** right after a station checkpoint (no declared pause).\n"
                "Ask **minimally** about the homework — one short sentence or weave into the next question — no long interrogation.\n"
                "Then continue the stage work."
            )

    if not blocks:
        return ""

    return "".join(blocks)


def build_station_wrap_instruction(state: Dict[str, Any], language: str) -> str:
    """When time-eligible, instruct model what to do IF it advances the step this turn."""
    if not station_time_anchor_eligible(state):
        return ""
    if language == "he":
        return (
            "\n\n# נקודת עצירה בתחנה (רלוונטי רק אם **בתשובה זו** אתה **מקדם** את `current_step` לשלב חדש "
            f"מבין {', '.join(sorted(STATION_ENTRY_STEPS))})\n"
            "אם **כן** — בתוך `coach_message` כללו בסגנון חם: התעניינות קצרה במה שהיה, סיכום קומה מעריך, "
            "משימת השהיה הבאה ברורה, הוקרה קצרה («כל הכבוד על הדרך שלך!» או ניסוח דומה), "
            "ובנוסף משפט שמבהיר שאפשר **לעצור כאן** או **להמשיך** — בלי לחסום.\n"
            "במקביל **חובה** למלא ב־`internal_state` את השדות `shehiya_mission_title` ו־`shehiya_mission_body` "
            "(כותרת קצרה + 2–4 משפטים מעשיים) — הם יוצגו במסך התובנות ובכרטיס המשימה.\n"
            "אם **לא** מקדמים שלב בתשובה זו — השאר את שני שדות השהיה כ־null."
        )
    return (
        "\n\n# Station checkpoint (only if **this** response **advances** `current_step` into a new milestone among "
        f"{', '.join(sorted(STATION_ENTRY_STEPS))})\n"
        "If yes — in `coach_message` include warmly: brief check-in, appreciative floor summary, "
        "clear next homework, short praise, plus one sentence that stopping here **or** continuing is both OK — non-blocking.\n"
        "You **must** fill `shehiya_mission_title` and `shehiya_mission_body` in `internal_state` (short title + 2–4 actionable sentences) "
        "for the Insights panel and mission card.\n"
        "If you do **not** advance the step this turn — leave both shehiya fields null."
    )


def maybe_commit_station_checkpoint(
    state: Dict[str, Any],
    old_step: str,
    new_step: str,
    internal_state: Dict[str, Any],
    language: str,
) -> Optional[Dict[str, Any]]:
    """
    If a station checkpoint should fire, mutate state (timestamps, active_shehiya, dedupe) and
    return a JSON-serializable payload for the HTTP client. Otherwise return None.
    """
    if old_step == new_step:
        return None
    if new_step not in STATION_ENTRY_STEPS:
        return None
    if not station_time_anchor_eligible(state):
        return None
    if _already_offered_for_step(state, new_step):
        return None

    title = (internal_state.get("shehiya_mission_title") or "").strip()
    body = (internal_state.get("shehiya_mission_body") or "").strip()
    if not title or not body:
        fb_title, fb_body = _fallback_homework(new_step, language)
        title = title or fb_title
        body = body or fb_body

    now_iso = _utc_now().isoformat()
    state["last_station_checkpoint_at"] = now_iso
    _mark_offered(state, new_step)
    station_id = f"enter_{new_step}"
    state["active_shehiya"] = {
        "station_id": station_id,
        "step": new_step,
        "title": title,
        "body": body,
        "assigned_at": now_iso,
    }

    floor_title = station_title_for_step(new_step, language)
    payload = {
        "station_id": station_id,
        "step": new_step,
        "floor_title": floor_title,
        "homework_title": title,
        "homework_body": body,
        "language": language,
    }
    logger.info("[StationCheckpoint] Emitted checkpoint for step=%s", new_step)
    return payload


def consume_session_flow_flags(state: Dict[str, Any]) -> None:
    """Clear one-shot UI / prompt flags after they were used to build the coach turn."""
    sf = state.get("session_flow")
    if not isinstance(sf, dict):
        return
    if sf.get("paused_at_station"):
        sf["paused_at_station"] = False
    if sf.get("continued_immediately_next"):
        sf["continued_immediately_next"] = False
    state["session_flow"] = sf


def apply_station_intent(state: Dict[str, Any], intent: str) -> None:
    """Persist user choice from sticky bar (no LLM)."""
    sf = state.setdefault("session_flow", {})
    if intent == "pause_here":
        sf["paused_at_station"] = True
        sf["paused_at"] = _utc_now().isoformat()
        sf["continued_immediately_next"] = False
    elif intent == "continue_coaching":
        sf["paused_at_station"] = False
        sf["continued_immediately_next"] = True
        sf["continued_at"] = _utc_now().isoformat()
    else:
        raise ValueError(f"Unknown station intent: {intent}")
