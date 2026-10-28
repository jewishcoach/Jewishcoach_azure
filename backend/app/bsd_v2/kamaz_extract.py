"""
כמ"ז (S12): the traits that came up in the client's 3+3 answers, as suggestions for his 6+6 card.

Booklet p.28: the client gathers the traits from his own answers — so these are suggestions he taps, each with the
words it came from. Chips map by the fixed table (kamaz_bank.chip_traits, no model); free text goes through one
narrow call whose output is kept only when the trait is in the bank and the quote appears in his words. On any
failure: the chip traits alone — never an invented trait.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.bsd.llm import get_azure_chat_llm_4o_mini

from .kamaz_bank import NATURE_TRAITS, SOURCE_TRAITS, chip_traits, normalize_trait

logger = logging.getLogger(__name__)

EXTRACT_TIMEOUT_SECONDS = 10.0
_MAX_PER_SIDE = 6


class _Suggestion(BaseModel):
    trait: str = Field(description="שם תכונה מהמאגר, כפי שהוא כתוב ברשימה")
    quote: str = Field(description="המילים שלו שמהן עלתה התכונה — העתקה מדויקת, עד 12 מילים")


class _Extraction(BaseModel):
    source: List[_Suggestion] = Field(default_factory=list)
    nature: List[_Suggestion] = Field(default_factory=list)
    event_source: List[str] = Field(default_factory=list, description="עד 3 כוחות מקור מהמאגר, הרלוונטיים ביותר למצב שלו")
    event_nature: List[str] = Field(default_factory=list, description="עד 2 כוחות טבע מהמאגר, הרלוונטיים ביותר למצב שלו")


def _bank_lines(traits: List[Dict[str, str]]) -> str:
    return ", ".join(t["label"] for t in traits)


_PROMPT = (
    "אתה עוזר למאמן בתהליך השיבה. המתאמן השלים משפטים על המקור שלו (ערכים, אור) ועל הטבע שלו (צרכים ונטיות). "
    "זהה אילו תכונות **מהמאגר בלבד** עולות מהמילים שלו.\n"
    f"מאגר המקור: {_bank_lines(SOURCE_TRAITS)}.\n"
    f"מאגר הטבע: {_bank_lines(NATURE_TRAITS)}.\n"
    "כללים: רק תכונה שעולה בבירור ממה שכתב. כוח טבע הוא נטייה או צורך **במובן הבריא** — כשהוא כותב פחד או הימנעות, "
    "בחר את הצורך שמתחתיו (למשל חשש מדחייה → צורך בשייכות וקבלה), לעולם לא את הפחד עצמו. ב-`quote` העתק את המילים "
    "שלו מתוך **התשובה** (לא מהמשפט שהוא השלים) כפי שנכתבו. עד 6 בכל צד. ב-`event_source` / `event_nature` — מתוך המאגר, הכוחות שהכי יעזרו לו מול המצב "
    "שהוא עובד עליו (מתואר בהקשר)."
)

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", (text or "").strip()).strip(".,;:\"'״")


def _context_text(cd: Dict[str, Any]) -> str:
    stance = cd.get("stance") if isinstance(cd.get("stance"), dict) else {}
    parts = [
        ("האירוע", cd.get("event_description")),
        ("הדפוס", cd.get("pattern")),
        ("החוק הפנימי", cd.get("paradigm")),
        ("העמדה הישנה", stance.get("short") or stance.get("reality_belief")),
        ("מה העמדה נותנת לו", ", ".join(stance.get("gains") or [])),
        ("מה היא לוקחת ממנו", ", ".join(stance.get("losses") or [])),
        ("איך היה רוצה לפעול", cd.get("action_desired")),
    ]
    return "\n".join(f"{k}: {v}" for k, v in parts if v)


def _merge(base: List[Dict[str, str]], extra: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out = list(base)
    for s in extra:
        if len(out) >= _MAX_PER_SIDE:
            break
        if not any(x["trait"] == s["trait"] for x in out):
            out.append(s)
    return out[:_MAX_PER_SIDE]


def validate_extraction(raw: _Extraction, answers: List[Dict[str, Any]], cd: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only bank traits whose quote is in his words (answers or the conversation context)."""
    haystack = _norm(" ".join(a.get("text") or "" for a in answers)) + " " + _norm(_context_text(cd))
    out: Dict[str, Any] = {"suggested": {"source": [], "nature": []}, "event_rank": {"source": [], "nature": []}}
    for side, items in (("source", raw.source), ("nature", raw.nature)):
        for s in items:
            trait = normalize_trait(s.trait, side)
            quote = _norm(s.quote)
            # the quote ran into the sentence he completed — his answer alone is the quote
            whole = next((_norm(a.get("text")) for a in answers if a.get("text") and _norm(a.get("text")) in quote), None)
            if whole and quote not in haystack:
                quote = whole
            if not trait or len(quote) < 2 or quote not in haystack:
                continue
            if not any(x["trait"] == trait for x in out["suggested"][side]):
                out["suggested"][side].append({"trait": trait, "quote": quote[:160]})
    for side, items in (("source", raw.event_source), ("nature", raw.event_nature)):
        for t in items:
            trait = normalize_trait(t, side)
            if trait and trait not in out["event_rank"][side]:
                out["event_rank"][side].append(trait)
    return out


async def extract_kamaz(answers: List[Dict[str, Any]], cd: Dict[str, Any]) -> Dict[str, Any]:
    """{"suggested": {side: [{trait, quote}]}, "event_rank": {side: [trait]}} — chip traits first."""
    chips = chip_traits(answers)
    result: Dict[str, Any] = {"suggested": chips, "event_rank": {"source": [], "nature": []}}
    free = [a for a in answers or [] if (a.get("text") or "").strip()]
    if not free:
        return result
    lines = "\n".join(f"[{'מקור' if a.get('side') == 'source' else 'טבע'}] משפט: {a.get('prompt') or ''}\n"
                      f"תשובה: {a.get('text')}" for a in free)
    ctx = _context_text(cd)
    try:
        llm = get_azure_chat_llm_4o_mini().with_structured_output(_Extraction, method="function_calling")
        raw = await asyncio.wait_for(
            llm.ainvoke([SystemMessage(content=_PROMPT),
                         HumanMessage(content=f"התשובות שלו:\n{lines}" + (f"\n\nהקשר מהשיחה:\n{ctx}" if ctx else ""))]),
            timeout=EXTRACT_TIMEOUT_SECONDS,
        )
        checked = validate_extraction(raw, answers, cd)
    except Exception:
        logger.warning("[Kamaz] extraction failed — chip traits only", exc_info=True)
        return result
    for side in ("source", "nature"):
        result["suggested"][side] = _merge(chips[side], checked["suggested"][side])
    result["event_rank"] = checked["event_rank"]
    return result
