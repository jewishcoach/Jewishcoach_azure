"""
Stage Gates - Deterministic gate checking for each BSD stage.

Each gate function returns:
  - ok: bool (passed gate?)
  - extracted: dict (structured data)
  - missing: dict (what's missing)
"""

from typing import Dict, Any, Tuple
import re
from .stage_defs import StageId
from .state_schema import BsdState


# ==========================================
# DETECTION FUNCTIONS (Binary: exists or not)
# ==========================================

def detect_action_sequence(text: str) -> bool:
    """
    Detect if text contains an action sequence (event narrative).
    
    Simple heuristic: If text is long enough (>= 4 words) OR contains action verbs, it's likely a story.
    This is NOT perfect, but it's cautious and avoids blocking valid events.
    """
    text_lower = text.lower()
    word_count = len(text.split())
    
    # Heuristic 1: >= 4 words suggests a narrative
    # Examples: "היא יצאה מאוחר בלי רשותי" (5 words)
    if word_count >= 4:
        return True
    
    # Heuristic 2: contains sequence markers
    sequence_markers = [
        # Hebrew
        "ואז", "אחרי", "לפני", "כש", "אז", "לאחר", "ואחר", "ברגע",
        # English
        "then", "after", "before", "when", "while"
    ]
    if any(marker in text_lower for marker in sequence_markers):
        return True
    
    # Heuristic 3: contains action verbs (past tense)
    action_verbs = [
        # Hebrew past tense verbs
        "יצא", "יצאה", "אמר", "אמרה", "עשה", "עשתה", "הלך", "הלכה",
        "סירב", "סירבה", "צעק", "צעקה", "בכה", "בכתה",
        # English past tense verbs
        "went", "said", "did", "walked", "refused", "yelled", "cried", "asked"
    ]
    if any(verb in text_lower for verb in action_verbs):
        return True
    
    return False


def detect_other_people(text: str) -> bool:
    """
    Detect if text mentions other people.
    
    Looks for: ילד/ה, בן/בת, הוא/היא, מישהו, etc.
    """
    text_lower = text.lower()
    
    people_markers = [
        # Hebrew
        "ילד", "ילדה", "ילדים", "בן", "בת", "בני", "בני",
        "הוא", "היא", "הם", "הן",
        "אשתי", "בעלי", "אימא", "אבא", "אח", "אחות",
        "מישהו", "מישהי", "אנשים", "חבר", "חברה",
        "מנהל", "עובד", "קולגה", "שותף",
        # English
        "child", "kid", "son", "daughter",
        "he", "she", "they", "them",
        "wife", "husband", "mom", "dad", "brother", "sister",
        "someone", "people", "friend",
        "manager", "colleague", "partner"
    ]
    
    return any(marker in text_lower for marker in people_markers)


def detect_emotion_words(text: str) -> bool:
    """
    Detect if text mentions emotional experience.
    
    Looks for: כעסתי, פחדתי, נעלבתי, הרגשתי, etc.
    """
    text_lower = text.lower()
    
    emotion_markers = [
        # Hebrew emotions
        "כעס", "כעסתי", "כועס", "כועסת",
        "פחד", "פחדתי", "פוחד", "פוחדת",
        "עצב", "עצוב", "עצובה", "עצבתי",
        "שמח", "שמחה", "שמחתי",
        "נעלב", "נעלבתי", "נעלבה",
        "מתוסכל", "תסכול", "תסכולת",
        "מבולבל", "בלבול",
        "קנא", "קנאה", "קנאתי",
        "רגש", "הרגשתי", "מרגיש", "מרגישה",
        # English emotions
        "angry", "anger", "mad",
        "scared", "afraid", "fear",
        "sad", "sadness",
        "happy", "joy",
        "frustrated", "frustration",
        "confused", "confusion",
        "jealous", "jealousy",
        "felt", "feel", "feeling", "emotion"
    ]
    
    return any(marker in text_lower for marker in emotion_markers)


def detect_concept_word(text: str) -> bool:
    """
    Detect if text contains a meaningful concept/word (not just gibberish).
    
    Used for stages expecting concepts: S1 (topic), S6 (gap name), S7 (pattern).
    """
    text_stripped = text.strip()
    
    # Too short
    if len(text_stripped) < 2:
        return False
    
    # Only numbers (gibberish)
    if text_stripped.replace(" ", "").replace(",", "").isdigit():
        return False
    
    # Has at least one letter
    if any(c.isalpha() for c in text_stripped):
        return True
    
    return False


def looks_truncated(text: str) -> bool:
    """
    Generic heuristic to detect truncated/incomplete input.
    
    Used for stages expecting concepts/words (S1, S6-name, S7-pattern, etc.)
    
    Returns True if:
    - Very short (< 3 chars)
    - Looks like an incomplete word (no clear ending)
    
    Note: Not perfect, and that's OK. Goal is to be cautious, not overly clever.
    """
    t = text.strip()
    
    # Too short
    if len(t) < 3:
        return True
    
    # Single word with no clear ending (Hebrew/English heuristics)
    if t.isalpha() and len(t.split()) == 1:
        # Hebrew heuristic: common word endings
        # Complete endings: ות, ים, ה, ן, ת, ר, ל, י, ע, ק, ם, ך
        # Incomplete: ו (alone at end often means truncated like "הורו" instead of "הורות")
        hebrew_complete_endings = ("ות", "ים", "ה", "ן", "ת", "ר", "ל", "י", "ע", "ק", "ם", "ך", "יה", "ית", "יות")
        hebrew_incomplete_endings = ("ו", "וד", "וג", "וב")
        
        # Check for incomplete endings
        if any(t.endswith(end) for end in hebrew_incomplete_endings):
            return True
        
        # If doesn't end with complete ending, might be truncated
        if not any(t.endswith(end) for end in hebrew_complete_endings):
            # English heuristic (if ASCII)
            if t.isascii() and not t[-1].lower() in "aeiourstnldg":
                return True
    
    return False


def _simple_emotion_list(text: str) -> list[str]:
    """
    Extract emotions from text using simple heuristics.
    
    Strategy:
    1. First, try to extract emotions from "I feel X" patterns
    2. Then, split by commas/newlines for simple lists
    3. Normalize adjectives to noun forms (עצוב → עצב)
    
    Examples:
        "כעס, קנאה, תסכול" → ["כעס", "קנאה", "תסכול"]
        "אני עצוב לראות..." → ["עצב"]
        "אני דואג לעתידו" → ["דאגה"]
        "כעס\nתסכול" → ["כעס", "תסכול"]
    """
    text_lower = (text or "").strip().lower()
    
    # Emotion patterns: "I am/feel [emotion]" in Hebrew and English
    emotion_patterns = {
        # Hebrew: אני + [adjective] → extract root emotion
        r'\bאני\s+(עצוב|עצובה)\b': 'עצב',
        r'\bאני\s+(כועס|כועסת)\b': 'כעס',
        r'\bאני\s+(דואג|דואגת)\b': 'דאגה',
        r'\bאני\s+(מתוסכל|מתוסכלת)\b': 'תסכול',
        r'\bאני\s+(פוחד|פוחדת)\b': 'פחד',
        r'\bאני\s+(מבוייש|מבוישת)\b': 'בושה',
        r'\bאני\s+(אשם|אשמה)\b': 'אשמה',
        r'\bאני\s+(בודד|בודדה)\b': 'בדידות',
        r'\bאני\s+(קנא|קנאה)\b': 'קנאה',
        r'\bאני\s+(שמח|שמחה)\b': 'שמחה',
        # English: I am/feel [adjective]
        r'\bi\s+am\s+sad\b': 'sadness',
        r'\bi\s+am\s+angry\b': 'anger',
        r'\bi\s+am\s+worried\b': 'worry',
        r'\bi\s+feel\s+sad\b': 'sadness',
        r'\bi\s+feel\s+angry\b': 'anger',
        r'\bi\s+feel\s+frustrated\b': 'frustration',
    }
    
    extracted = []
    
    # Extract from patterns
    for pattern, emotion_noun in emotion_patterns.items():
        if re.search(pattern, text_lower):
            extracted.append(emotion_noun)
    
    # Also try simple comma-separated list
    # Split by commas, newlines, semicolons (NOT spaces!)
    parts = re.split(r"[,\n;]+", text.strip())
    items = [p.strip() for p in parts if p.strip()]
    
    # Filter out items that are only numbers/symbols (no letters)
    items = [i for i in items if any(ch.isalpha() for ch in i)]
    
    # Combine pattern-extracted + list items
    all_items = extracted + items
    
    # Deduplicate case-insensitive
    seen = set()
    out = []
    for i in all_items:
        key = i.lower()
        if key not in seen:
            seen.add(key)
            out.append(i)
    
    return out


def check_s0_gate(user_message: str, state: BsdState) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    S0: Coaching Contract - needs explicit consent.
    
    Returns:
        ok: True if explicit consent ("כן", "yes", "בטח", etc.)
        extracted: {}
        missing: {} if ok, {"consent": True} if missing
    """
    msg = user_message.strip().lower()
    
    # Explicit consent tokens
    consent_tokens = ["כן", "yes", "בטח", "אוקי", "ok", "אישור", "מאשר", "sure", "go ahead"]
    
    if any(tok in msg for tok in consent_tokens):
        return True, {}, {}
    
    # Missing consent
    return False, {}, {"consent": True}


def check_s2_gate(user_message: str, state: BsdState) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    S2: Event Isolation - needs a specific event with other people.
    
    CRITICAL: S2 does NOT require emotion in the text!
    Emotion will be extracted in S3 (Emotion Screen).
    
    Architecture: Detection → Validation → Extraction (SEPARATE!)
    
    RELAXED: Accept if:
    - (has_event AND has_people) OR
    - (has_people AND is_long_enough [10+ words])
    
    Returns:
        ok: True if event has all required elements (event + people)
        extracted: {"event_description": str, ...}
        missing: {"event": bool, "people": bool} if incomplete
    """
    text = user_message.strip()
    
    # ===================
    # 1️⃣ DETECTION (binary checks, no extraction!)
    # ===================
    has_event = detect_action_sequence(text)
    has_people = detect_other_people(text)
    is_long_enough = len(text.split()) >= 10  # 10+ words
    # NOTE: We do NOT require emotion in S2! Emotion comes in S3.
    
    # ===================
    # 2️⃣ VALIDATION (based ONLY on detection!)
    # ===================
    # RELAXED: Accept if:
    # - Traditional: has_event AND has_people
    # - OR Flexible: has_people AND is_long_enough (allows natural descriptions)
    if (has_event and has_people) or (has_people and is_long_enough):
        # ===================
        # 3️⃣ EXTRACTION (what to save, doesn't affect validation!)
        # ===================
        extracted = {
            "event_description": text,  # Save full text (unstructured)
        }
        
        # Status: OK_UNSTRUCTURED
        # Meaning: User provided content that answers the stage,
        # but data is not fully structured yet (that happens in S3-S5).
        return True, extracted, {}
    
    # Missing something - LOOP
    missing = {}
    if not has_event:
        missing["event"] = True
    if not has_people:
        missing["people"] = True
    
    return False, {}, missing


def check_s1_gate(user_message: str, state: BsdState) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    S1: Topic - needs a clear topic (not just "don't know" or truncated).
    
    Returns:
        ok: True if topic is clear and complete
        extracted: {"topic": str}
        missing: {"confirm_topic": True} if looks truncated, {"topic": True} if missing
    """
    msg = user_message.strip()
    
    # Too short
    if len(msg) < 2:
        return False, {}, {"topic": True}
    
    # Check for "don't know" patterns
    dont_know = ["לא יודע", "לא בטוח", "לא ידוע", "don't know", "not sure", "no idea"]
    if any(dk in msg.lower() for dk in dont_know):
        return False, {}, {"topic": True}
    
    # Check if looks truncated/incomplete
    if looks_truncated(msg):
        return False, {"topic": msg}, {"confirm_topic": True}
    
    # Valid topic
    return True, {"topic": msg}, {}


def check_s3_gate(user_message: str, state: BsdState) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    S3: Emotions - needs >= 3 emotions (ACCUMULATED across loops).
    
    RELAXED: Changed from 4 to 3 emotions (BSD methodology: 3-4 emotions)
    
    Returns:
        ok: True if accumulated >= 3 emotions
        extracted: {"emotions_list": [...]}
        missing: {"emotions_count": int} if < 3
    """
    # Get existing emotions
    existing = []
    if state.cognitive_data and state.cognitive_data.event_actual:
        existing = state.cognitive_data.event_actual.emotions_list or []
    
    # Parse new emotions
    new_emotions = _simple_emotion_list(user_message)
    
    # Merge unique
    merged = existing.copy()
    for e in new_emotions:
        if e not in merged:
            merged.append(e)
    
    # Check count (RELAXED: 3 instead of 4)
    if len(merged) >= 3:
        return True, {"emotions_list": merged}, {}
    else:
        return False, {"emotions_list": merged}, {"emotions_count": 3 - len(merged)}


def check_s4_gate(user_message: str, state: BsdState) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    S4: Thought - needs a verbal thought (sentence), not emotions.
    
    Returns:
        ok: True if has a sentence/thought
        extracted: {"thought": str}
        missing: {"thought": True} if missing
    """
    msg = user_message.strip()
    
    # Too short
    if len(msg) < 3:
        return False, {}, {"thought": True}
    
    # Check if it's just an emotion (single word from emotions)
    emotion_patterns = ["כעס", "קנאה", "תסכול", "יאוש", "בושה", "פחד", "anger", "fear", "sad"]
    words = msg.split()
    if len(words) == 1 and any(pat in msg.lower() for pat in emotion_patterns):
        return False, {}, {"thought": True}
    
    # Valid thought
    return True, {"thought": msg}, {}


def check_s5_gate(user_message: str, state: BsdState) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    S5: Action - needs TWO separate descriptions:
    1. ACTUAL: What user actually did (מצוי)
    2. DESIRED: What user wanted to do/feel/think (רצוי)
    
    This is a TWO-TURN stage:
    - First turn: Get actual action
    - Second turn: Get desired state
    
    Architecture: Detection → Validation → Extraction (SEPARATE!)
    
    Returns:
        ok: True if BOTH actual AND desired are present
        extracted: {"action_actual": str} or {"action_desired": str} or both
        missing: {"action_actual": True} or {"action_desired": True}
    """
    msg = user_message.strip()
    
    # Get existing data from state
    existing_actual = None
    existing_desired = None
    if state.cognitive_data and state.cognitive_data.event_actual:
        existing_actual = state.cognitive_data.event_actual.action_content
    if state.cognitive_data and state.cognitive_data.event_desired:
        existing_desired = getattr(state.cognitive_data.event_desired, 'action_content', None)
    
    # ===================
    # 1️⃣ DETECTION
    # ===================
    has_content = len(msg) >= 3 and any(c.isalpha() for c in msg)
    
    # Detect if this is a "desired" statement (contains want/wish words)
    desired_markers = ["רוצה", "הייתי רוצה", "רציתי", "אשמח", "חלמתי", "want", "wish", "would like", "hope"]
    is_desired = any(marker in msg.lower() for marker in desired_markers)
    
    # ===================
    # 2️⃣ VALIDATION & EXTRACTION
    # ===================
    if not has_content:
        # Empty input
        if not existing_actual:
            return False, {}, {"action_actual": True}
        else:
            return False, {}, {"action_desired": True}
    
    # If we don't have actual yet, this is the actual
    if not existing_actual and not is_desired:
        return False, {"action_actual": msg}, {"action_desired": True}
    
    # If we have actual but not desired, this is the desired
    if existing_actual and not existing_desired:
        return True, {"action_desired": msg}, {}
    
    # If this looks like desired but we don't have actual yet
    if is_desired and not existing_actual:
        # User jumped to desired! Ask for actual first
        return False, {}, {"action_actual": True}
    
    # If user provides both in one message (rare but possible)
    if not existing_actual and not existing_desired and is_desired:
        # Extract both (split by newline or period)
        parts = msg.split('\n') if '\n' in msg else [msg]
        if len(parts) >= 2:
            return True, {"action_actual": parts[0], "action_desired": parts[1]}, {}
        else:
            # Only has desired, missing actual
            return False, {"action_desired": msg}, {"action_actual": True}
    
    # Default: treat as actual if not clear
    if not existing_actual:
        return False, {"action_actual": msg}, {"action_desired": True}
    else:
        return True, {"action_desired": msg}, {}


def check_s6_gate(user_message: str, state: BsdState) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    S6: Gap - needs gap name (score is helpful but not blocking).
    
    Architecture: Detection → Validation → Extraction (SEPARATE!)
    
    Returns:
        ok: True if has gap name (even without score!)
        extracted: {"gap_name": str, "gap_score": int | None}
        missing: {"confirm_gap_name": True} if truncated, {"gap_name": True} if missing
    """
    msg = user_message.strip()
    
    # ===================
    # 1️⃣ DETECTION
    # ===================
    has_concept = detect_concept_word(msg)
    
    # Try to detect score (helpful but not required)
    score_match = re.search(r'\b([1-9]|10)\b', msg)
    has_score = score_match is not None
    
    # ===================
    # 2️⃣ VALIDATION (based ONLY on detection!)
    # ===================
    
    # Extract name for validation
    name = None
    if score_match:
        # Remove score to get name
        name = msg.replace(score_match.group(0), "").strip()
        name = re.sub(r'[/,:\-]+', ' ', name).strip()
    else:
        name = msg if len(msg) > 2 else None
    
    # Check if truncated (needs confirmation)
    if name and looks_truncated(name):
        return False, {"gap_name": name}, {"confirm_gap_name": True}
    
    # If has concept, ACCEPT (even without score!)
    if has_concept and name and len(name) >= 2:
        # ===================
        # 3️⃣ EXTRACTION
        # ===================
        score = int(score_match.group(1)) if score_match else None
        extracted = {
            "gap_name": name,
            "gap_score": score  # May be None!
        }
        return True, extracted, {}
    
    # Missing gap name
    return False, {}, {"gap_name": True}


def check_gate(stage: str, user_message: str, state: BsdState) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    Main gate checking dispatcher.
    
    Args:
        stage: Current stage ID
        user_message: User's message
        state: Current BSD state (for accumulation)
    
    Returns:
        (ok, extracted, missing)
    """
    try:
        stage_id = StageId(stage)
    except ValueError:
        return False, {}, {}
    
    if stage_id == StageId.S0:
        return check_s0_gate(user_message, state)
    elif stage_id == StageId.S1:
        return check_s1_gate(user_message, state)
    elif stage_id == StageId.S2:
        return check_s2_gate(user_message, state)
    elif stage_id == StageId.S3:
        return check_s3_gate(user_message, state)
    elif stage_id == StageId.S4:
        return check_s4_gate(user_message, state)
    elif stage_id == StageId.S5:
        return check_s5_gate(user_message, state)
    elif stage_id == StageId.S6:
        return check_s6_gate(user_message, state)
    else:
        # Stages without deterministic gates (S2, S7-S10) - use LLM
        return False, {}, {}


# Public API
__all__ = ["check_gate"]

