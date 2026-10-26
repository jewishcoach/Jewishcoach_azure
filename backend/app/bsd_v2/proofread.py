"""
Silent proofreading of the client's sentences that are quoted back later and enter the coaching-request card
(the pattern, the old stance, the new stance, the request's situation and result).

The coach model was asked to "fix the Hebrew" inside its own turn and inverted meaning ("אם לא… לא" → "אם…"), so
this is a separate, narrow call, and its output is kept only when it is a light edit of the original: the same
negations, mostly the same words, about the same length. Anything else — or any error — keeps the original.
"""

import asyncio
import difflib
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.bsd.llm import get_azure_chat_llm_4o_mini

logger = logging.getLogger(__name__)

PROOFREAD_TIMEOUT_SECONDS = 8.0

_PROMPT = (
    "אתה מגיה עברית. קיבלת משפט שכתב אדם על עצמו. תקן **רק** שגיאות הקלדה, כתיב ותחביר בולטות — "
    "התאמה בין גוף, מין ומספר, מילית או אות חסרה, צירוף שבור. לדוגמה: 'ויישארו לי לבד' → 'ואשאר לבד'.\n"
    "אסור: לשנות משמעות, להפוך שלילה לחיוב או להפך, להחליף מילים במילים נרדפות, להוסיף תוכן, לקצר, "
    "לשנות גוף (נשאר 'אני' אם כתוב 'אני'), או לשפר סגנון.\n"
    "אם המשפט תקין — החזר אותו בדיוק כמו שהוא. החזר את המשפט בלבד, בלי מרכאות ובלי הסבר."
)

_HE = "֐-׿"
_NEGATION = re.compile(rf"(?<![{_HE}])[ושכה]?(?:לא|אין|אינני|אינו|אינה|בלי|אל|אף|מעולם)(?![{_HE}])")
_WORD = re.compile(rf"[{_HE}a-zA-Z0-9]+")

_cache: dict[str, str] = {}
_CACHE_MAX = 2000


def _acceptable(src: str, out: str) -> bool:
    if not out or "\n" in out or len(out) > 1.25 * len(src) + 4 or len(out) < 0.8 * len(src) - 4:
        return False
    if len(_NEGATION.findall(src)) != len(_NEGATION.findall(out)):
        return False
    a, b = _WORD.findall(src), _WORD.findall(out)
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


async def proofread_he(text: str) -> str:
    """The sentence with glaring typos/grammar fixed, or the original when unsure."""
    src = (text or "").strip()
    if len(_WORD.findall(src)) < 3:
        return text
    if src in _cache:
        return _cache[src]
    out = src
    try:
        resp = await asyncio.wait_for(
            get_azure_chat_llm_4o_mini().ainvoke([SystemMessage(content=_PROMPT), HumanMessage(content=src)]),
            timeout=PROOFREAD_TIMEOUT_SECONDS,
        )
        cand = (getattr(resp, "content", "") or "").strip().strip("\"'״“”")
        if _acceptable(src, cand):
            out = cand
        elif cand != src:
            logger.info("[Proofread] rejected edit: %r → %r", src[:120], cand[:120])
    except Exception:
        logger.warning("[Proofread] failed — keeping the original", exc_info=True)
        return text  # not cached: a later turn may succeed
    if len(_cache) >= _CACHE_MAX:
        _cache.clear()
    _cache[src] = out
    _cache[out] = out  # the stored result is not proofread again next turn
    return out


async def proofread_request_texts(cd: dict) -> bool:
    """Proofread the stored quotes that reach the final card, in place. True when the coaching request changed."""
    targets: list[tuple[dict, str]] = []
    stance = cd.get("stance")
    if isinstance(stance, dict):
        targets += [(stance, k) for k in ("reality_belief", "short") if isinstance(stance.get(k), str)]
    for k in ("pattern", "renewal_belief"):
        if isinstance(cd.get(k), str):
            targets.append((cd, k))
    req = cd.get("coaching_request")
    req_keys = ("situation", "old", "new", "result")
    if isinstance(req, dict):
        targets += [(req, k) for k in req_keys if isinstance(req.get(k), str)]
    todo = [(d, k) for d, k in targets if d[k].strip() and _cache.get(d[k].strip()) != d[k].strip()]
    if not todo:
        return False
    fixed = await asyncio.gather(*(proofread_he(d[k]) for d, k in todo))
    req_changed = False
    for (d, k), new in zip(todo, fixed):
        if new != d[k]:
            req_changed = req_changed or d is req
            d[k] = new
    return req_changed
