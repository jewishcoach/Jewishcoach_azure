"""
כמ"ז (S12) — the trait bank and the 3+3 discovery questions, in one place.

Source: the S12 spec "אפיון כמ"ז בתוך אימון 3+3" (questions based on booklet p.25; bank and chip→trait mapping as
written there). Each trait has a display `label` and a `short` form — the short form is what is stored in
`forces` and read inside the coaching request ("…אפעל מתוך המקור שלי, שהוא כנות" — not "אמת / כנות").
Open for the expert: the two mappings marked REVIEW below, and the short forms.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

SOURCE_TRAITS: List[Dict[str, str]] = [
    {"group": "חיבור ואהבה", "label": "אהבה", "short": "אהבה"},
    {"group": "חיבור ואהבה", "label": "חמלה", "short": "חמלה"},
    {"group": "חיבור ואהבה", "label": "נתינה", "short": "נתינה"},
    {"group": "חיבור ואהבה", "label": "הכלה", "short": "הכלה"},
    {"group": "חיבור ואהבה", "label": "מסירות", "short": "מסירות"},
    {"group": "אמת ועוצמה פנימית", "label": "אמת / כנות", "short": "כנות"},
    {"group": "אמת ועוצמה פנימית", "label": "אומץ", "short": "אומץ"},
    {"group": "אמת ועוצמה פנימית", "label": "יושרה", "short": "יושרה"},
    {"group": "אמת ועוצמה פנימית", "label": "ענווה", "short": "ענווה"},
    {"group": "אמת ועוצמה פנימית", "label": "נחישות", "short": "נחישות"},
    {"group": "אמון והובלה", "label": "אמונה", "short": "אמונה"},
    {"group": "אמון והובלה", "label": "אמון", "short": "אמון"},
    {"group": "אמון והובלה", "label": "אחריות", "short": "אחריות"},
    {"group": "אמון והובלה", "label": "שליחות", "short": "שליחות"},
    {"group": "אמון והובלה", "label": "מנהיגות / הובלה", "short": "הובלה"},
    {"group": "אמון והובלה", "label": "נאמנות", "short": "נאמנות"},
    {"group": "חיות ויצירה", "label": "שמחה", "short": "שמחה"},
    {"group": "חיות ויצירה", "label": "יצירתיות", "short": "יצירתיות"},
    {"group": "חיות ויצירה", "label": "חופש", "short": "חופש"},
    {"group": "חיות ויצירה", "label": "סקרנות / למידה", "short": "סקרנות"},
    {"group": "חיות ויצירה", "label": "הכרת הטוב", "short": "הכרת הטוב"},
    {"group": "חיות ויצירה", "label": "אופטימיות / תקווה", "short": "תקווה"},
]

NATURE_TRAITS: List[Dict[str, str]] = [
    {"group": "שמירה והגנה עצמית", "label": "זהירות", "short": "זהירות"},
    {"group": "שמירה והגנה עצמית", "label": "צורך בביטחון ויציבות", "short": "צורך בביטחון ויציבות"},
    {"group": "שמירה והגנה עצמית", "label": "שמירה על עצמי", "short": "שמירה על עצמי"},
    {"group": "שמירה והגנה עצמית", "label": "מחושבות / בדיקת גבולות", "short": "מחושבות"},
    {"group": "יחסים, שייכות ושקט", "label": "שאיפה להרמוניה ושקט", "short": "שאיפה להרמוניה ושקט"},
    {"group": "יחסים, שייכות ושקט", "label": "צורך בשייכות וקבלה", "short": "צורך בשייכות וקבלה"},
    {"group": "יחסים, שייכות ושקט", "label": "רגישות לתגובות הסביבה", "short": "רגישות לתגובות הסביבה"},
    {"group": "יחסים, שייכות ושקט", "label": "רצון להיטיב ולשמור על שלום", "short": "רצון להיטיב ולשמור על שלום"},
    {"group": "שליטה, סדר וביצוע", "label": "צורך בשליטה וודאות", "short": "צורך בשליטה וודאות"},
    {"group": "שליטה, סדר וביצוע", "label": "יסודיות ודיוק", "short": "יסודיות ודיוק"},
    {"group": "שליטה, סדר וביצוע", "label": "מעשיות / פרקטיות", "short": "מעשיות"},
    {"group": "שליטה, סדר וביצוע", "label": "שאיפה למצוינות", "short": "שאיפה למצוינות"},
    {"group": "כבוד, גבולות ומרחב", "label": "צורך בהערכה וכבוד", "short": "צורך בהערכה וכבוד"},
    {"group": "כבוד, גבולות ומרחב", "label": "שמירה על גבולות וצדק", "short": "שמירה על גבולות וצדק"},
    {"group": "כבוד, גבולות ומרחב", "label": "עצמאות (נטייה להסתדר לבד)", "short": "עצמאות"},
    {"group": "כבוד, גבולות ומרחב", "label": "ערנות וקליטת ניואנסים", "short": "ערנות וקליטת ניואנסים"},
    {"group": "כבוד, גבולות ומרחב", "label": "צורך במרחב וחופש פעולה", "short": "צורך במרחב וחופש פעולה"},
]


def _chip(cid: str, text: str, maps_to: List[str], text_f: Optional[str] = None) -> Dict[str, Any]:
    return {"id": cid, "text": text, "text_f": text_f or text, "maps_to": maps_to}


DISCOVERY_QUESTIONS: List[Dict[str, Any]] = [
    {"id": "s1", "side": "source", "title": "נוכחות ומתנה",
     "prompt": "הדבר הטוב והאור שאני מביא איתי באופן טבעי לכל מקום הם...",
     "prompt_f": "הדבר הטוב והאור שאני מביאה איתי באופן טבעי לכל מקום הם...",
     "chips": [
         _chip("s1a", "אווירה טובה, שמחה וחיוך", ["שמחה", "תקווה"]),
         _chip("s1b", "הקשבה אמיתית ולב פתוח", ["הכלה", "אהבה"]),
         _chip("s1c", "סדר, בהירות ולקיחת אחריות", ["אחריות"]),
         _chip("s1d", "אנרגיה של עשייה והובלה", ["הובלה"]),
         _chip("s1e", "כנות, אמת ודיבור בגובה העיניים", ["כנות", "ענווה"]),
         _chip("s1f", "חשיבה יצירתית ורעיונות חדשים", ["יצירתיות"]),
     ]},
    {"id": "s2", "side": "source", "title": "מקור חיות ושמחה",
     "prompt": "אני מתמלא שמחה וחיות כשאני פועל מתוך...",
     "prompt_f": "אני מתמלאת שמחה וחיות כשאני פועלת מתוך...",
     "chips": [
         _chip("s2a", "חיבור עמוק ואמיתי לאנשים", ["אהבה", "אמון"]),
         _chip("s2b", "תחושת חופש וביטוי עצמי", ["חופש"]),
         _chip("s2c", "למידה, סקרנות וגילוי דברים חדשים", ["סקרנות"]),
         _chip("s2d", "משמעות ושליחות שגדולה ממני", ["שליחות", "אמונה"]),
         _chip("s2e", "נתינה ועזרה מכל הלב", ["נתינה", "חמלה"]),
         _chip("s2f", "אומץ ליצור ולבנות משהו חדש", ["אומץ", "יצירתיות"]),
     ]},
    {"id": "s3", "side": "source", "title": "מראת הקרובים וההצלחות",
     "prompt": "אם נשאל את האנשים הקרובים אליי מהי המעלה הכי חזקה שלי (שגם עוזרת לי להצליח), הם יגידו...",
     "chips": [
         _chip("s3a", "שאפשר לסמוך עליי בעיניים עצומות", ["נאמנות", "אחריות"]),
         _chip("s3b", "שיש לי לב ענק, חמלה ורגישות", ["אהבה", "חמלה"]),
         _chip("s3c", "שאני אדם ישר, אמיתי ונאמן לעצמי", ["יושרה", "כנות"]),
         _chip("s3d", "שאני מסור ולא מוותר גם כשקשה", ["מסירות", "נחישות"], "שאני מסורה ולא מוותרת גם כשקשה"),
         # REVIEW (expert): "ענווה" here may be a stretch — the chip reads as הכלה alone
         _chip("s3e", "שאני יודע להכיל ולהקשיב בלי לשפוט", ["הכלה", "ענווה"], "שאני יודעת להכיל ולהקשיב בלי לשפוט"),
         _chip("s3f", "שיש בי אמונה ותקווה שמחזקות אחרים", ["אמונה", "הכרת הטוב"]),
     ]},
    {"id": "n1", "side": "nature", "title": "ויתור, ריצוי ויחסים",
     "prompt": "כשאני מוותר לעצמי כדי לא להיכנס לעימות או כדי לרצות אחרים, מה שמפעיל אותי מבפנים הוא...",
     "prompt_f": "כשאני מוותרת לעצמי כדי לא להיכנס לעימות או כדי לרצות אחרים, מה שמפעיל אותי מבפנים הוא...",
     "chips": [
         _chip("n1a", "הצורך שלי בשקט תעשייתי והרמוניה", ["שאיפה להרמוניה ושקט"]),
         _chip("n1b", "רגישות גבוהה למה שיחשבו או יגידו עליי", ["רגישות לתגובות הסביבה"]),
         _chip("n1c", "הצורך להרגיש שייך, אהוב ורצוי", ["צורך בשייכות וקבלה"], "הצורך להרגיש שייכת, אהובה ורצויה"),
         _chip("n1d", "רצון להיטיב ולדאוג שכולם יהיו מרוצים", ["רצון להיטיב ולשמור על שלום"]),
         _chip("n1e", "ערנות וקליטת כל ניואנס במצב הרוח של האחר", ["ערנות וקליטת ניואנסים"]),
         # REVIEW (expert): maybe "שאיפה להרמוניה ושקט" rather than space
         _chip("n1f", "תחושה שאין לי כוח למאבקים ודרמות", ["צורך במרחב וחופש פעולה"]),
     ]},
    {"id": "n2", "side": "nature", "title": "שליטה, קירות וביצוע",
     "prompt": "ה'קיר' שאני נתקל בו שוב ושוב, או המקום שבו הכי קשה לי לשחרר שליטה, הוא...",
     "prompt_f": "ה'קיר' שאני נתקלת בו שוב ושוב, או המקום שבו הכי קשה לי לשחרר שליטה, הוא...",
     "chips": [
         _chip("n2a", "קושי עם אי-ודאות וצורך לדעת איך דברים יסתיימו", ["צורך בשליטה וודאות"]),
         _chip("n2b", "פחד לטעות ורצון שהכל ייעשה מדויק ומושלם", ["יסודיות ודיוק", "שאיפה למצוינות"]),
         _chip("n2c", "תחושה שאם לא אעשה הכל לבד – זה לא יקרה", ["עצמאות"]),
         _chip("n2d", "חשש משינויים וצורך ביציבות וביטחון", ["צורך בביטחון ויציבות"]),
         _chip("n2e", "צורך להביא תוצאות מעשיות ומהירות בשטח", ["מעשיות"]),
         _chip("n2f", "תחושת מחנק כשמציבים לי מסגרות לוחצות", ["צורך במרחב וחופש פעולה"]),
     ]},
    {"id": "n3", "side": "nature", "title": "פחד, גבולות וכבוד",
     "prompt": "כשפוגעים בכבוד שלי, חוצים לי גבול (כמו עני שקיבל 5 ש\"ח ודורש 30 ש\"ח) או כשאני מרגיש מאוים, "
               "הנטייה הראשונה שלי היא...",
     "prompt_f": "כשפוגעים בכבוד שלי, חוצים לי גבול (כמו עני שקיבל 5 ש\"ח ודורש 30 ש\"ח) או כשאני מרגישה מאוימת, "
                 "הנטייה הראשונה שלי היא...",
     "chips": [
         _chip("n3a", "להיזהר, לבחון בחשדנות ולשמור מרחק", ["זהירות"]),
         _chip("n3b", "להתרגז על חוסר הצדק ולעמוד על הגבול שלי", ["שמירה על גבולות וצדק"]),
         _chip("n3c", "להיפגע מכך שלא מעריכים ולא מכבדים אותי", ["צורך בהערכה וכבוד"]),
         _chip("n3d", "להיסגר ולהגן על עצמי מפני פגיעה או חולשה", ["שמירה על עצמי"]),
         _chip("n3e", "להתכווץ ולתת מתוך אי-נעימות", ["רצון להיטיב ולשמור על שלום"]),
         _chip("n3f", "לבדוק בזהירות את הגבולות לפני שאני פועל", ["מחושבות"], "לבדוק בזהירות את הגבולות לפני שאני פועלת"),
     ]},
]

_BANK = {"source": SOURCE_TRAITS, "nature": NATURE_TRAITS}
_SPACES = re.compile(r"\s+")


def _key(text: str) -> str:
    return _SPACES.sub(" ", (text or "").strip().strip(".,;:\"'״"))


def normalize_trait(text: str, side: Optional[str] = None) -> Optional[str]:
    """A trait in the bank — by its short form, its label, or either half of a "X / Y" label — as its short form."""
    k = _key(text)
    if not k:
        return None
    for s in ([side] if side else ["source", "nature"]):
        for t in _BANK[s]:
            parts = {t["short"], t["label"], *[p.strip() for p in t["label"].split("/")],
                     t["label"].split("(")[0].strip()}
            if k in parts:
                return t["short"]
    return None


def side_of(short: str) -> Optional[str]:
    for s, traits in _BANK.items():
        if any(t["short"] == short for t in traits):
            return s
    return None


def questions_for(gender: Optional[str]) -> List[Dict[str, Any]]:
    """The 6 questions as sent to the card, in the client's gender (chip ids stay the same)."""
    fem = gender == "female"
    out = []
    for q in DISCOVERY_QUESTIONS:
        out.append({
            "id": q["id"], "side": q["side"], "title": q["title"],
            "prompt": q.get("prompt_f", q["prompt"]) if fem else q["prompt"],
            "chips": [{"id": c["id"], "text": c["text_f"] if fem else c["text"]} for c in q["chips"]],
        })
    return out


def bank_for_card() -> Dict[str, List[Dict[str, str]]]:
    return {"source": [dict(t) for t in SOURCE_TRAITS], "nature": [dict(t) for t in NATURE_TRAITS]}


def chip_traits(answers: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
    """Traits of the chips the client used — fixed mapping, no model. Quote = the chip text he kept in his answer."""
    chips = {c["id"]: (c, q) for q in DISCOVERY_QUESTIONS for c in q["chips"]}
    out: Dict[str, List[Dict[str, str]]] = {"source": [], "nature": []}
    for a in answers or []:
        for cid in a.get("chips_used") or []:
            hit = chips.get(cid)
            if not hit:
                continue
            chip, q = hit
            for short in chip["maps_to"]:
                if not any(x["trait"] == short for x in out[q["side"]]):
                    out[q["side"]].append({"trait": short, "quote": (a.get("text") or chip["text"]).strip()[:160]})
    return out
