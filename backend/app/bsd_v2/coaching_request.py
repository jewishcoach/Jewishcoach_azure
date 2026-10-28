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
    # "קושי לבטא…" after "הקושי להתמודד עם" doubled the word ("…להתמודד עם קושי לבטא") — "הקושי שלי לבטא…"
    t = re.sub(r"^(?:ה?קושי(?:\s+שלי)?)\s+", "", t)
    first = t.split()[0] if t.split() else ""
    if re.match(r"^(?:ה?קושי)", (text or "").strip()) and first.startswith("ל"):
        return f"הקושי שלי {t}"
    if t.startswith("כש"):
        # the situation only — "כשאני מרגישה לא מוערכת…, אני נשארת לבד" left the main clause hanging in the request
        t = re.sub(r",\s*(?:אז\s+|ואז\s+)?(?:אני|אז)\s.*$", "", t)
        return f"הקושי להתמודד עם הרגעים ש{t[2:]}"
    if first.startswith("ל") and len(first) >= 4 and first not in _NOT_INFINITIVE:
        return f"הקושי שלי {t}"
    if first == "לא":
        return f"הקושי שלי ש{t}"
    return f"הקושי להתמודד עם {t}"


def he_list(items: list) -> str:
    """"כנות ונאמנות", "אומץ, כנות ונתינה" — the last one joined with ו (a comma read as two separate clauses)."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " ו" + items[-1]


def compose_coaching_request(data: Dict[str, Any]) -> str:
    """The booklet's complex coaching request (p.37-38), as one sentence in the client's words."""
    name, that, old_adj, new_adj = _REQUEST_FLOOR_HE.get(data.get("floor"), _REQUEST_FLOOR_HE["stance"])
    def as_list(v: Any) -> list:  # the API accepts a string too — joining a str listed it letter by letter
        return [v] if isinstance(v, str) else list(v or [])
    source = he_list([x.strip() for x in as_list(data.get("source")) if x and x.strip()])
    nature = he_list([x.strip() for x in as_list(data.get("nature")) if x and x.strip()])
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
