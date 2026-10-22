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


def _situation(text: str) -> str:
    """The template expects a noun phrase ("להתמודד עם ישיבות צוות"); "כשאני במפגש צוות…" → "הרגעים שאני במפגש…"."""
    t = (text or "").strip().rstrip(".")
    return f"הרגעים ש{t[2:]}" if t.startswith("כש") else t


def compose_coaching_request(data: Dict[str, Any]) -> str:
    """The booklet's complex coaching request (p.37-38), as one sentence in the client's words."""
    name, that, old_adj, new_adj = _REQUEST_FLOOR_HE.get(data.get("floor"), _REQUEST_FLOOR_HE["pattern"])
    source = ", ".join(s for s in (data.get("source") or []) if s)
    nature = ", ".join(s for s in (data.get("nature") or []) if s)
    noun = name[1:]  # "הדפוס" → "דפוס" for "מופיע הדפוס הישן שלי"
    # booklet wording (p.37-38): "אני מבקש להתאמן על הקושי להתמודד עם [תיאור הסיטואציה]"
    parts = [f"אני מבקש/ת להתאמן על הקושי להתמודד עם {_situation(data.get('situation') or '')}"]
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
