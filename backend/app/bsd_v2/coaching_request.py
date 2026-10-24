"""
The booklet's complex coaching request (p.37-38), composed from the client's own words.

Shared by the tools router (the request card) and the coach (S15: the answer to "מה מתוך זה תלוי בך" updates
only the result, and the request is recomposed — the model had overwritten the whole request with that answer).
"""
import re
from typing import Any, Dict

_REQUEST_FLOOR_HE = {"pattern": ("הדפוס", "שהוא", "הישן", "החדש"), "paradigm": ("הפרדיגמה", "שהיא", "הישנה", "החדשה"),
                     "stance": ("העמדה", "שהיא", "הישנה", "החדשה")}


def _request_clause(text: str) -> str:
    """A first-person sentence ("אני מאמין ש…") reads inside the template only as a quote: שהיא "אני מאמין ש…"."""
    t = re.sub(r"^\s*(?:כן|נכון|אכן)[,.]?\s+", "", (text or "").strip()).rstrip(".")  # "כן, אני שותק…" (S8 answer)
    first_words = t.split()[:4]  # "בעזרת ה', אני מגיב…" is first person too
    return f'"{t}"' if t.startswith("העמדה שלי") or "אני" in first_words else t


_NOT_INFINITIVE = ("לחץ", "לחצים", "לילה", "לילות", "לימודים", "לב")


def _difficulty(text: str) -> str:
    """The booklet's opening (p.37): "הקושי להתמודד עם [סיטואציה]" for a noun phrase; a verb phrase reads as "הקושי
    שלי לדבר על…" ("להתמודד עם לדבר" was ungrammatical); "כשאני…" → "הקושי להתמודד עם הרגעים שאני…"."""
    t = (text or "").strip().rstrip(".")
    first = t.split()[0] if t.split() else ""
    if t.startswith("כש"):
        return f"הקושי להתמודד עם הרגעים ש{t[2:]}"
    if first.startswith("ל") and len(first) >= 4 and first not in _NOT_INFINITIVE:
        return f"הקושי שלי {t}"
    if first == "לא":
        return f"הקושי שלי ש{t}"
    return f"הקושי להתמודד עם {t}"


def compose_coaching_request(data: Dict[str, Any]) -> str:
    """The booklet's complex coaching request (p.37-38), as one sentence in the client's words."""
    name, that, old_adj, new_adj = _REQUEST_FLOOR_HE.get(data.get("floor"), _REQUEST_FLOOR_HE["stance"])
    source = ", ".join(s for s in (data.get("source") or []) if s)
    nature = ", ".join(s for s in (data.get("nature") or []) if s)
    noun = name[1:]  # "הדפוס" → "דפוס" for "מופיע הדפוס הישן שלי"
    # booklet wording (p.37-38): "אני מבקש להתאמן על הקושי להתמודד עם [תיאור הסיטואציה]"
    parts = [f"אני מבקש/ת להתאמן על {_difficulty(data.get('situation') or '')}"]
    if (data.get("old") or "").strip():
        parts.append(f"שכאשר מופיע{'ה' if that == 'שהיא' else ''} ה{noun} {old_adj} שלי, {that} {_request_clause(data['old'])}")
    if source:
        parts.append(f"אפעל מתוך המקור שלי, שהוא {source}")
    if nature:
        parts.append(f"ומתוך הטבע שלי, שהוא {nature}")
    if (data.get("new") or "").strip():
        parts.append(f"ומתוך ה{noun} {new_adj} שבחרתי, {that} {_request_clause(data['new'])}")
    parts.append(f"כדי שהתוצאה שאשיג תהיה: {(data.get('result') or '').strip()}")
    return ", ".join(p.rstrip(".,") for p in parts) + "."
