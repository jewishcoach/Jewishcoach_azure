"""
Conversational Coach - Natural, flowing coaching conversation layer.

Purpose: Replace rigid scripts with natural, contextual coaching dialogue.

This layer sits ABOVE the router/gates and transforms structured decisions
into natural, human-like coaching conversations.
"""

from typing import Dict, Any, Optional
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from .llm import get_chat_llm
from .state_schema import BsdState
from .stage_context_builder import build_stage_context
from .stage_defs import StageId
from .few_shot_examples import get_few_shot_examples
from .insight_analyzer import analyze_response, InsightAnalysis

logger = logging.getLogger(__name__)


async def generate_natural_response(
    *,
    stage: str,
    language: str,
    user_message: str,
    intent: str,
    decision: str,
    next_stage: Optional[str],
    cognitive_data: Dict[str, Any],
    missing: Dict[str, Any],
    state: BsdState,  # NEW: for insight analysis
    user_name: Optional[str] = None,
    user_gender: Optional[str] = None,
    loop_count: int = 0,  # For stuck-loop detection
) -> str:
    """
    Generate a natural, flowing coaching response (NOT a rigid script).
    
    This is the "soul" of the coach - it uses LLM with high temperature
    to create natural, contextual, varied responses that feel human.
    
    Key principles:
    1. NO rigid scripts - every response is contextual
    2. Gentle transitions - not "now we'll do X"
    3. Natural language - not robotic
    4. Respectful - follows Clean Language principles
    
    Args:
        stage: Current BSD stage
        language: "he" or "en"
        user_message: What the user said
        intent: Router's classification (ANSWER_OK, ANSWER_PARTIAL, etc.)
        decision: advance or loop
        next_stage: Where we're going (if advancing)
        cognitive_data: What we know so far (topic, emotions, etc.)
        missing: What's missing (if partial)
        
    Returns:
        Natural, contextual coaching response
    """
    
    # Use warm LLM for natural conversation
    llm = get_chat_llm(purpose="talker")  # temp=0.35
    
    # 🧠 NEW: Analyze response for coaching insights
    # This provides deep psychological analysis BEFORE we generate response
    # ⚡ OPTIMIZATION: Only run for stages S1-S5 (not S0, S2_READY, etc.)
    # IMPORTANT: S1 included to detect EXTERNAL_ATTRIBUTION ("אשתי אומרת שאני לא רומנטי")
    analysis: Optional[InsightAnalysis] = None
    stages_needing_analysis = {"S1", "S2", "S3", "S4", "S5"}
    
    if stage in stages_needing_analysis:
        try:
            analysis = await analyze_response(
                user_message=user_message,
                stage=stage,
                language=language,
                state=state
            )
            logger.info(
                f"🧠 [INSIGHT ANALYSIS] Depth={analysis.depth_score:.1f}/10, "
                f"Engagement={analysis.engagement_quality.value}, "
                f"Insights={len(analysis.insights)}"
            )
            if analysis.insights:
                for insight in analysis.insights:
                    logger.warning(
                        f"  💡 [{insight.type.value}] (severity={insight.severity:.2f}): "
                        f"{insight.observation}"
                    )
        except Exception as e:
            logger.error(f"[INSIGHT ANALYSIS ERROR] {e}")
            analysis = None
    else:
        logger.info(f"⚡ [INSIGHT ANALYSIS] Skipped for stage {stage} (optimization)")
    
    # Build context summary
    context_summary = _build_context_summary(cognitive_data, stage, language)
    
    # Detect vulnerable moments (harsh self-thoughts)
    is_vulnerable = await _detect_vulnerable_moment(user_message, stage, language)
    
    # Build situation description
    # ✨ NEW: Pass loop_count and user_message for stuck-loop and confusion detection
    situation = _describe_situation(
        stage=stage,
        intent=intent,
        decision=decision,
        next_stage=next_stage,
        missing=missing,
        language=language,
        is_vulnerable=is_vulnerable,
        loop_count=loop_count,
        user_message=user_message
    )
    
    # ✨ NEW APPROACH: Few-Shot Examples FIRST!
    # This teaches the LLM by EXAMPLE, not by 200 lines of "don't do X"
    few_shot = get_few_shot_examples(language)
    
    sys = SystemMessage(content=(
        f"{few_shot}\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Critical Coaching Principles (Keep these in mind):\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "⚠️ ONE QUESTION PER TURN:\n"
        "- Ask ONE thing, wait for answer\n"
        "- Don't stack multiple questions\n"
        "- ❌ WRONG: 'What did you think? And how did you feel?'\n"
        "- ✅ RIGHT: 'What did you think?' [wait] → [next turn] 'And how did you feel?'\n"
        "\n"
        "🎭 VARY YOUR LANGUAGE:\n"
        "- ❌ DON'T repeat the same phrases turn after turn\n"
        "- ❌ BAD: 'I hear that...' → 'I hear that...' → 'I hear that...'\n"
        "- ✅ GOOD: Mix it up! 'I hear...' → 'Okay, [topic]' → 'Tell me more...' → Direct question\n"
        "- ❌ DON'T: 'This sounds like...' × 5 times\n"
        "- ✅ DO: Sometimes reflect, sometimes paraphrase, sometimes ask directly\n"
        "\n"
        "🔄 NEVER GO BACKWARDS:\n"
        "- If you have TOPIC → never ask for it again\n"
        "- If you have EVENT → never ask for it again\n"
        "- If you have 4+ EMOTIONS → never ask for more\n"
        "- Check the Context Summary before asking!\n"
        "\n"
        "💬 REFLECT, DON'T INTERPRET:\n"
        "- Repeat back EXACTLY what they said\n"
        "- Don't assume emotions they didn't mention\n"
        "- Don't interpret their words\n"
        "- ✅ 'I hear you said X. Tell me more.'\n"
        "- ❌ 'It sounds like you're feeling X'\n"
        "\n"
        "💔 VULNERABLE MOMENTS (CRITICAL!):\n"
        "- If user says: 'אני לא ראוי', 'אני אפס', 'I'm not worthy', 'I'm worthless':\n"
        "  🔴 THIS IS NOT A REGULAR RESPONSE!\n"
        "  ❌ DON'T jump to 'עכשיו בוא נסתכל על מה שקרה בפועל'\n"
        "  ✅ DO: Repeat their EXACT thought\n"
        "  ✅ DO: 'זו מחשבה כבדה' / 'This is a heavy thought'\n"
        "  ✅ DO: 'תודה שאתה משתף' / 'Thanks for sharing'\n"
        "  ✅ DO: Pause before asking about action\n"
        "- Even if you already asked about thoughts, NEW harsh thought = NEW vulnerable moment!\n"
        "\n"
        "🧭 METHODOLOGICAL EXPLANATIONS (when natural):\n"
        "- Sometimes explain WHY you're asking (but not every time!):\n"
        "  → 'To understand your experience in reality, not just as concept'\n"
        "  → 'When we experience a moment, there are emotions, thoughts, and actions - let's understand them'\n"
        "- Don't lecture! Keep it conversational and brief (1-2 sentences)\n"
        "- See Examples 1.5 and 2.5 for natural explanations\n"
        "\n"
        "🛑 PAUSE & SUMMARIZE:\n"
        "- After user shares thought (S4): DON'T jump immediately to action!\n"
        "- Repeat their thought, then SUMMARIZE: 'So we have: event X, you felt Y, you thought Z'\n"
        "- Give a moment to breathe before moving forward\n"
        "- See Example 4.7 for non-vulnerable thought + summary\n"
        "\n"
        "❌ FORBIDDEN:\n"
        "- Emojis (🎯❌✅) - robotic!\n"
        "- 'It sounds like...' - interpretation!\n"
        "- '[TOPIC] is broad!' - rejecting!\n"
        "- 'ככל ש...כך...' - formal!\n"
        "- Multiple questions in one turn\n"
        "- Examples in parentheses\n"
        "\n"
        "✅ USE INSTEAD:\n"
        "- Simple, direct questions\n"
        "- 'אוקיי', 'ספר לי', 'מה...?'\n"
        "- 'Okay', 'Tell me', 'What...?'\n"
        "- 2-3 sentences max\n"
        "- Warm, present, curious\n"
        "\n"
        f"LANGUAGE: {language}\n"
        f"- {'Hebrew: Spoken (בוא, אוקיי), NOT formal (הבה, כעת)' if language == 'he' else 'English: Conversational (Okay, Tell me), NOT academic (Let us examine)'}\n"
    ))
    
    # Add gender information to the system prompt if available
    gender_instruction = ""
    if language == "he" and user_gender:
        if user_gender == "male":
            gender_instruction = (
                "\nGENDER ADAPTATION:\n"
                "The user is MALE. Use MALE forms in Hebrew:\n"
                "- תהיה (not תהיי)\n"
                "- ספציפי (not ספציפית)\n"
                "- אתה (not את)\n"
                "- תרצה (not תרצי)\n"
            )
        elif user_gender == "female":
            gender_instruction = (
                "\nGENDER ADAPTATION:\n"
                "The user is FEMALE. Use FEMALE forms in Hebrew:\n"
                "- תהיי (not תהיה)\n"
                "- ספציפית (not ספציפי)\n"
                "- את (not אתה)\n"
                "- תרצי (not תרצה)\n"
            )
    
    if gender_instruction:
        sys = SystemMessage(content=sys.content + gender_instruction)
    
    # ✨ NEW: Inject stage-specific context from RAG (examples from the book!)
    stage_context = None
    try:
        # Convert string stage to StageId enum
        stage_id = StageId(stage) if isinstance(stage, str) else stage
        stage_context = await build_stage_context(stage_id, language)
        
        if stage_context:
            # Add stage context to system message
            sys = SystemMessage(content=sys.content + "\n\n" + stage_context)
            logger.info(f"✅ [CONVERSATIONAL] Injected stage context for {stage_id}")
    except Exception as e:
        logger.warning(f"⚠️ [CONVERSATIONAL] Could not load stage context: {e}")
        # Continue without stage context - not critical
    
    # Build insight alert section (if any critical insights)
    insight_alert = ""
    if analysis and analysis.insights:
        high_severity_insights = [i for i in analysis.insights if i.severity >= 0.6]
        if high_severity_insights:
            if language == "he":
                insight_alert = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                insight_alert += "🚨 התראות קריטיות - קרא בעיון!\n"
                insight_alert += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            else:
                insight_alert = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                insight_alert += "🚨 CRITICAL ALERTS - READ CAREFULLY!\n"
                insight_alert += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            for insight in high_severity_insights:
                insight_alert += f"\n📌 {insight.observation}\n"
                insight_alert += f"💭 {insight.interpretation}\n"
                insight_alert += f"🎯 ACTION: {insight.suggestion}\n"
                
                # SPECIAL: Make CUMULATIVE_PATTERN extra visible
                if insight.type.value == "cumulative_pattern":
                    if language == "he":
                        insight_alert += "\n⚠️ זה דורש שינוי בגישה! אל תבקש 'רגע' עוד פעם!\n"
                    else:
                        insight_alert += "\n⚠️ This requires approach change! Don't ask for 'moment' again!\n"
                
                # SPECIAL: Make EXTERNAL_ATTRIBUTION extra visible (CRITICAL for S1!)
                if insight.type.value == "external_attribution":
                    if language == "he":
                        insight_alert += "\n🛑 זה לא נושא אימון אמיתי! המתאמן מצטט אחרים, לא מבטא רצון אישי!\n"
                        insight_alert += "🎯 אמור: 'אני שומע מה X אומר. אבל מה **אתה** רוצה? על מה **אתה** רוצה להתאמן?'\n"
                        insight_alert += "🛑 אל תעבור ל-S2! נשאר ב-S1 עד שהמתאמן מביע רצון אישי!\n"
                    else:
                        insight_alert += "\n🛑 This is not a real coaching topic! User is quoting others, not expressing own desire!\n"
                        insight_alert += "🎯 Say: 'I hear what X says. But what do **you** want? What do **you** want to work on?'\n"
                        insight_alert += "🛑 Don't move to S2! Stay in S1 until user expresses own desire!\n"
            
            insight_alert += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    human = HumanMessage(content=(
        f"Context Summary:\n{context_summary}\n"
        f"{insight_alert}"
        f"\n"
        f"Current Situation:\n{situation}\n"
        f"\n"
        f"User just said: \"{user_message}\"\n"
        f"\n"
        f"Generate a natural coaching response that:\n"
        f"- Reflects what they said\n"
        f"- Guides them toward the next step\n"
        f"- Feels like a real conversation\n"
        f"- ⚠️ CRITICAL: If there are alerts above - YOU MUST FOLLOW THEM! Don't ignore the suggestions!\n"
        f"\n"
        f"Response (2-4 sentences, natural flow):"
    ))
    
    try:
        response = await llm.ainvoke([sys, human])
        text = (response.content or "").strip()
        
        logger.info(f"[CONVERSATIONAL] Generated natural response ({len(text.split())} words)")
        return text
        
    except Exception as e:
        logger.error(f"[CONVERSATIONAL ERROR] Failed to generate: {e}")
        # Fallback to simple reflection
        if language == "he":
            return f"שמעתי אותך. {user_message}"
        else:
            return f"I hear you. {user_message}"


async def _detect_vulnerable_moment(user_message: str, stage: str, language: str) -> bool:
    """
    GENERIC vulnerability detector using LLM (no hardcoded word lists).
    
    Detects if user shared a harsh/painful self-thought that requires
    special care and acknowledgment before proceeding.
    
    Uses LLM to understand MEANING, not match words.
    """
    # Check if message contains vulnerable thought markers
    # Even if we're past S4, user might share additional harsh thoughts!
    vulnerable_markers_he = ["לא ראוי", "לא שווה", "אפס", "כישלון", "לא טוב", "פגום", "נשבר"]
    vulnerable_markers_en = ["not worthy", "worthless", "failure", "not good enough", "broken", "defective"]
    
    markers = vulnerable_markers_he if language == "he" else vulnerable_markers_en
    has_marker = any(marker in user_message.lower() for marker in markers)
    
    # Only check if:
    # 1. We're in S4/S5 (thought/action stages), OR
    # 2. Message contains vulnerable markers (user shared harsh thought even if past S4)
    if stage not in ["S4", "S5", "S6"] and not has_marker:
        return False
    
    # Skip if message is too short (likely not vulnerable)
    if len(user_message.strip()) < 5:
        return False
    
    # Skip simple confirmations
    if user_message.strip().lower() in ["כן", "yes", "נכון", "correct", "בטח", "sure"]:
        return False
    
    # Use cold LLM for classification (temp=0 for consistency)
    from .llm import get_chat_llm
    llm = get_chat_llm(purpose="reasoner")  # temp=0
    
    prompt_he = """סווג את המחשבה הבאה:

מחשבה: "{message}"

האם זו מחשבה **פגיעה/כואבת/חשופה** שדורשת הכרה עדינה?

קריטריונים ל-VULNERABLE:
✓ ביקורת עצמית קשה ("אני אפס", "אני כישלון", "אני אבא לא טוב")
✓ תחושת רגרסיה/חוסר שליטה ("אני הופך לילד", "אני תינוק")
✓ בושה/חוסר ערך עצמי ("אני לא שווה", "אני לא ראוי", "אני גרוע", "אני לא ראוי לדברים טובים")
✓ תחושת אשמה/פגם ("זה אשמתי", "אני פגום")
✓ חשיפת פגיעות עמוקה ("אני נשבר", "אני לא מסוגל")

קריטריונים ל-NOT VULNERABLE:
✗ תיאור עובדתי של מחשבה רגילה ("חשבתי שהוא כועס")
✗ ניתוח/הסבר ("זה בגלל...", "אני חושב ש...")
✗ שאלה או בירור ("למה זה קרה?")

השב **רק** במילה אחת:
- VULNERABLE
- NOT_VULNERABLE"""

    prompt_en = """Classify this thought:

Thought: "{message}"

Is this a **vulnerable/painful/exposed** thought requiring gentle acknowledgment?

VULNERABLE criteria:
✓ Harsh self-criticism ("I'm worthless", "I'm a failure")
✓ Regression/loss of control ("I become a child", "I'm a baby")
✓ Shame/unworthiness ("I'm not good enough", "I'm bad")
✓ Guilt/defectiveness ("It's my fault", "I'm broken")
✓ Deep vulnerability exposure ("I'm falling apart", "I can't cope")

NOT VULNERABLE criteria:
✗ Factual thought description ("I thought he was angry")
✗ Analysis/explanation ("It's because...", "I think that...")
✗ Question or clarification ("Why did this happen?")

Answer with **one word only**:
- VULNERABLE
- NOT_VULNERABLE"""

    prompt = prompt_he if language == "he" else prompt_en
    
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt.format(message=user_message))])
        result = (response.content or "").strip().upper()
        
        is_vulnerable = "VULNERABLE" in result and "NOT" not in result
        
        if is_vulnerable:
            logger.info(f"💔 [VULNERABLE DETECTED] '{user_message[:50]}...'")
        
        return is_vulnerable
        
    except Exception as e:
        logger.error(f"[VULNERABLE DETECTION ERROR] {e}")
        # Fail-safe: if LLM fails, don't block the flow
        return False


def _build_context_summary(cognitive_data: Dict[str, Any], stage: str, language: str) -> str:
    """Build a COMPREHENSIVE summary of what we know about the user so far."""
    parts = []
    
    # Topic (S1)
    topic = cognitive_data.get("topic")
    if topic:
        if language == "he":
            parts.append(f"✓ נושא: {topic}")
        else:
            parts.append(f"✓ Topic: {topic}")
    
    # Event (S2)
    event_actual = cognitive_data.get("event_actual", {})
    event_desc = event_actual.get("description")
    if event_desc:
        if language == "he":
            parts.append(f"✓ אירוע: {event_desc[:80]}...")
        else:
            parts.append(f"✓ Event: {event_desc[:80]}...")
    
    # Emotions (S3)
    emotions = event_actual.get("emotions_list", [])
    if emotions:
        emotions_str = ", ".join(emotions[:6])
        if language == "he":
            parts.append(f"✓ רגשות ({len(emotions)}): {emotions_str}")
        else:
            parts.append(f"✓ Emotions ({len(emotions)}): {emotions_str}")
    
    # Thought (S4)
    thought = event_actual.get("thought_content")
    if thought:
        if language == "he":
            parts.append(f"✓ מחשבה: \"{thought[:60]}...\"")
        else:
            parts.append(f"✓ Thought: \"{thought[:60]}...\"")
    
    # Action (S5 part 1)
    action = event_actual.get("action_content")
    if action:
        if language == "he":
            parts.append(f"✓ מעשה: {action[:60]}...")
        else:
            parts.append(f"✓ Action: {action[:60]}...")
    
    # Desired (S5 part 2)
    event_desired = cognitive_data.get("event_desired", {})
    desired = event_desired.get("action_content")
    if desired:
        if language == "he":
            parts.append(f"✓ רצוי: {desired[:60]}...")
        else:
            parts.append(f"✓ Desired: {desired[:60]}...")
    
    if not parts:
        if language == "he":
            return "תחילת התהליך (אין מידע עדיין)"
        else:
            return "Beginning of process (no data yet)"
    
    return "\n".join(parts)


def _describe_situation(
    stage: str,
    intent: str,
    decision: str,
    next_stage: Optional[str],
    missing: Dict[str, Any],
    language: str,
    is_vulnerable: bool = False,
    loop_count: int = 0,
    user_message: str = ""
) -> str:
    """Describe the current coaching situation for the LLM."""
    
    # Add stage-specific guidance
    stage_guidance = _get_stage_guidance(stage, language)
    
    # Add vulnerability note if detected
    vulnerability_note = ""
    if is_vulnerable:
        if language == "he":
            vulnerability_note = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 VULNERABLE MOMENT - רגע חשוף ופגיע
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
המשתמש שיתף תובנה עמוקה וכואבת על עצמו!

זה לא רגע "לעבור הלאה" - זה רגע לתת מקום.

מה לעשות:
1. חזור על המחשבה המדויקת שלו
2. הכר בכובד שלה: "זו מחשבה כבדה"
3. אשר אותו: "תודה שאתה משתף אותי בזה"
4. ❌ אל תקפוץ מיד לשלב הבא!
5. ✅ שאל: "זה מה שאמרת לעצמך באותו רגע?"

דוגמה: ראה דוגמה 4.5 למעלה.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            vulnerability_note = "\n🔴 VULNERABLE MOMENT: User shared deeply painful insight about themselves. This is not a moment to 'move on' - give it space. Repeat their exact thought, acknowledge its weight, thank them, and DON'T jump to next question immediately!"
    
    # ✨ NEW: Detect stuck loop and confusion
    stuck_loop_guidance = ""
    confusion_guidance = ""
    
    # Debug logging
    logger.warning(f"🔍 [ADAPTIVE] loop_count={loop_count}, user_message={user_message[:50]}")
    
    # STUCK LOOP: After 3 loops, MUST change approach!
    if loop_count >= 3:
        logger.warning(f"🚨 [STUCK LOOP DETECTED] loop_count={loop_count}! Activating adaptive guidance...")
        if language == "he":
            stuck_loop_guidance = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 STUCK LOOP ALERT! המתאמן ענה {loop_count} פעמים אבל עדיין לא עברנו הלאה.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

זה אומר שהגישה הנוכחית לא עובדת! חובה לשנות אסטרטגיה:

1. הכר בבעיה: "אני רואה שלא הצלחתי להבהיר"
2. הסבר למה אתה שואל: "אני שואל את זה כי..."
3. תן דוגמה קונקרטית: "לדוגמה: אתמול ב..."
4. שאל בצורה פשוטה יותר

❌ לעולם אל תחזור על אותה שאלה שוב!
✅ שנה את הדרך, לא את השלב!
""".format(loop_count=loop_count)
        else:
            stuck_loop_guidance = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 STUCK LOOP ALERT! User answered {loop_count} times but we haven't moved forward.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This means current approach isn't working! MUST change strategy:

1. Acknowledge: "I see I haven't been clear"
2. Explain why: "I'm asking this because..."
3. Give concrete example: "For example: yesterday at..."
4. Ask in simpler way

❌ NEVER repeat the same question again!
✅ Change the approach, not the stage!
"""
    
    # CONFUSION: User explicitly says they don't understand
    confusion_markers_he = ["לא מבין", "מה זאת אומרת", "מה הכוונה", "באותו רגע שמה", "לא ברור", "באיזה רגע", "מתי"]
    confusion_markers_en = ["don't understand", "what do you mean", "what does that mean", "not clear"]
    
    confusion_markers = confusion_markers_he if language == "he" else confusion_markers_en
    is_confused = any(marker in user_message.lower() for marker in confusion_markers)
    
    logger.warning(f"🔍 [CONFUSION CHECK] is_confused={is_confused}, markers_found={[m for m in confusion_markers if m in user_message.lower()]}")
    
    if is_confused:
        logger.warning(f"💭 [CONFUSION DETECTED] User is confused! Activating explanation guidance...")
        if language == "he":
            confusion_guidance = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💭 המתאמן מבולבל - הוא לא מבין את השאלה!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

חובה:
1. הכר: "אני מבין שזה לא היה ברור"
2. הסבר למה: "בוא אסביר למה אני שואל..."
3. השתמש במשל: "זה כמו..."
4. תן דוגמה: "לדוגמה: ..."
5. רק אז שאל שוב בפשטות

❌ אל תחזור על אותה שאלה מילולית!
✅ הסבר, הבהר, ורק אז שאל אחרת!
"""
        else:
            confusion_guidance = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💭 User is confused - they don't understand the question!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MUST:
1. Acknowledge: "I see that wasn't clear"
2. Explain why: "Let me explain why I'm asking..."
3. Use metaphor: "It's like..."
4. Give example: "For example: ..."
5. Only then ask again simply

❌ Don't repeat the same question literally!
✅ Explain, clarify, then ask differently!
"""
    
    if language == "he":
        if decision == "advance":
            base = f"המשתמש עמד בדרישות השלב.\n{stage_guidance}\nהכוון אותו בעדינות לשלב הבא."
            return stuck_loop_guidance + confusion_guidance + base + vulnerability_note
        elif intent == "ANSWER_PARTIAL":
            missing_str = ", ".join(missing.keys())
            return stuck_loop_guidance + confusion_guidance + f"תשובה חלקית. חסר: {missing_str}.\n{stage_guidance}\nבקש זאת בצורה טבעית." + vulnerability_note
        elif intent == "CLARIFY":
            return stuck_loop_guidance + confusion_guidance + f"המשתמש מבקש הבהרה.\n{stage_guidance}\nהסבר בקצרה ושאל שוב." + vulnerability_note
        elif intent == "OFFTRACK":
            return stuck_loop_guidance + confusion_guidance + f"התשובה לא רלוונטית.\n{stage_guidance}\nהנחה בעדינות חזרה לנושא." + vulnerability_note
        else:
            return stuck_loop_guidance + confusion_guidance + f"{stage_guidance}\nהמשך את השיחה באופן טבעי." + vulnerability_note
    else:
        if decision == "advance":
            base = f"User met requirements.\n{stage_guidance}\nGently guide to next stage."
            return stuck_loop_guidance + confusion_guidance + base + vulnerability_note
        elif intent == "ANSWER_PARTIAL":
            missing_str = ", ".join(missing.keys())
            return stuck_loop_guidance + confusion_guidance + f"Partial answer. Missing: {missing_str}.\n{stage_guidance}\nRequest naturally." + vulnerability_note
        elif intent == "CLARIFY":
            return stuck_loop_guidance + confusion_guidance + f"User asks for clarification.\n{stage_guidance}\nExplain briefly and ask again." + vulnerability_note
        elif intent == "OFFTRACK":
            return stuck_loop_guidance + confusion_guidance + f"Response not relevant.\n{stage_guidance}\nGently guide back to topic." + vulnerability_note
        else:
            return stuck_loop_guidance + confusion_guidance + f"{stage_guidance}\nContinue conversation naturally." + vulnerability_note


def _get_stage_guidance(stage: str, language: str) -> str:
    """Get stage-specific guidance for natural conversation."""
    if language == "he":
        guidance = {
            "S0": "שלב הרשות: וודא שיש רשות מפורשת להתחיל.",
            "S1": "שלב הנושא: בקש נושא לאימון. נושאים תקפים: ✓ 'היכולת שלי להצליח בעסקים' ✓ 'הובלה של פרויקט' ✓ 'רומנטיות' ✓ 'הורות' ✓ 'קבלת החלטות'. דחה רק: ❌ 'לא יודע' ❌ שאלות ❌ סירוב. ⚠️ CRITICAL: אם decision='loop' (נושא רחב כמו 'זוגיות', 'הורות', 'עסקים') - שאל שאלת מיקוד אנושית ומגוונת! אל תאמר 'זה תחום רחב!' (רובוטי). במקום זה, שאל בצורה טבעית וסקרנית: 'מה בזוגיות מעסיק אותך?' או 'איזה חלק מההורות תרצה לחקור?' או 'ספר לי יותר - מה בעסקים?' **וריאציה חשובה!** כל פעם שאל אחרת! 🛑 STOP LOOP: אם loop_count > 2 - אל תשאל 'מה בX?' שוב! במקום זה, קבל את מה שהמשתמש אמר כנושא (גם אם לא מושלם) והסבר את התהליך ועבור ל-S2! ⚠️ CRITICAL כשעוברים ל-S2 (decision='advance'): **חובה להסביר את התהליך קודם!** (ראה דוגמה 1.6): 'תראה, הדרך שלנו: ניקח רגע ספציפי, נכנס לעומק (רגשות-מחשבה-מעשה), זה יראה את הדפוס ואיך לשנות'. אחר כך שאל 'יש רגע כזה?' אל תקפוץ ישר לבקש אירוע בלי הסבר!",
            "S2": "שלב האירוע: בקש אירוע ספציפי אחד. CRITICAL: אירוע = רגע מסוים בזמן (מתי? עם מי? מה קרה?) לא מצב כללי! ❌ 'יש פרויקט שאני עובד עליו' = מצב כללי. ✓ 'אתמול בפגישה אמרתי X' = אירוע ספציפי. אם המשתמש נתן מצב כללי - בקש דוגמה **לרגע אחד** שקרה השבוע. אל תעבור לרגשות בלי אירוע ספציפי!",
            "S2_READY": "בדיקת נכונות (המנוע השלישי): שלב זה בודק אם יש אנרגיה להמשיך. ⚠️ אל תשתמש בסקריפט הרקוד 'לפני שנמשיך 3 שאלות'! תשאל בצורה טבעית וחופשית: (1) עד כמה חשוב שהמצב ישתנה? (2) האם שינוי אפשרי? (3) האם את/ה מסוגל/ת לעשות את השינוי? **וריאציה חשובה!** כל פעם שאל אחרת: 'אני רוצה לבדוק משהו', 'רגע לפני שממשיכים', 'יש לי כמה שאלות'. CRITICAL: אם 'לא מסוגל'/'אין כוח' → STOP! הסבר שאימון דורש יש (לא אין), אולי צריך תמיכה/ריפוי קודם.",
            "S3": "שלב הרגשות: בקש לפחות 4 רגשות שהיו באותו רגע.",
            "S4": "שלב המחשבה: בקש מחשבה מילולית (משפט פנימי).",
            "S5": "שלב המעשה והרצוי: שלב זה כולל שני חלקים. אם המשתמש כבר נתן את שני החלקים (מעשה + רצוי) והולכים לעבור ל-S2_READY → **עשה שיקוף מלא של המצוי**: 'אז יש לנו תמונה: [אירוע קצר], הרגשת [רגשות], חשבת [מחשבה], ועשית [מעשה]. זה נכון?' אחרי שהמשתמש מאשר, מעבר ל-S2_READY. אם חסר חלק - בקש אותו.",
            "S6": "שלב הפער: עכשיו כשיש לך המצוי (אירוע+רגשות+מחשבה+מעשה) והרצוי, עזור למשתמש לזהות את הפער ולתת לו שם + ציון 1-10. CRITICAL: אם המשתמש נותן ציון (למשל '5') - אל תפרש אותו! ❌ אל תגיד 'הציון שלך היה 5 בפגישה'. ✅ פשוט קבל את הציון ושאל לשם של הפער או עבור לשלב הבא. DON'T INTERPRET! אל תבקש אירוע שוב!",
            "S7": "שלב הדפוס: עזור לזהות דפוס חוזר ואמונה (פרדיגמה).",
            "S8": "שלב העמדה: עזור לזהות רווח והפסד מהעמדה. שאל: מה מרוויח? מה מפסיד? זו טבלת רווח והפסד פשוטה.",
            "S9": "שלב הכוחות (כמ\"ז): זהה כוחות מקור (ערכים, אמונות) וטבע (כישורים, יכולות). זה כרטיס המהות-זהות.",
            "S11": "שלב הבחירה החדשה: עזור למשתמש לבחור עמדה/פרדיגמה/דפוס חדשים. זו הקומה החדשה שלו.",
            "S12": "שלב החזון: עזור למשתמש לראות את התמונה הגדולה - שליחות, יעוד, חפץ הלב. זה מעבר לאירוע אחד.",
            "S10": "שלב המחויבות: בנה מחויבות לפעולה בנוסחה המלאה (קושי + מקור/טבע + תוצאה).",
        }
    else:
        guidance = {
            "S0": "Permission stage: Ensure explicit consent to begin.",
            "S1": "Topic stage: Ask for coaching topic. BE EXTREMELY LENIENT! Valid: ✓ 'my ability to succeed in business' ✓ 'project leadership' ✓ 'romance' ✓ 'parenting'. Reject only: ❌ 'I don't know' ❌ questions ❌ refusal. CRITICAL: If topic is 'broad' (like 'romance', 'business') - don't reject! Accept it and move DIRECTLY to ask for **specific event** that happened recently in this topic. Don't ask for 'more specific topic'!",
            "S2": "Event stage: Request ONE specific event. You can briefly explain WHY we need a specific event (see Example 1.5) - 'to understand your experience, not just as abstract concept, but in reality'. ACCEPT: ✓ 'I went on a date, got nervous, made mistakes'. REJECT: ❌ 'I have a project' (general), ❌ 'Last week I didn't go out' (non-event). Don't keep asking 'when exactly' if they already described what happened. When moving to emotions (S3), you can explain WHY we're going into details of emotion-thought-action (see Example 2.5) - but not every time, only when natural.",
            "S2_READY": "Readiness Check (The Engine): You come **after** the user described the full situation (event+emotions+thought+action). Now ask 3 questions: (1) How important is it that the situation changes (1-10)? (2) Is change possible? (3) Are **you capable** of making this change? CRITICAL: If user says 'I can't' or 'no strength' → STOP! Explain that coaching requires existing capacity (Yesh) and perhaps healing/supportive therapy is needed first. Otherwise → move to identify the gap (S6).",
            "S3": "Emotion stage: Request at least 4 emotions from that moment.",
            "S4": "Thought stage: Request verbal thought (internal sentence). AFTER user shares thought: (1) PAUSE - repeat their exact thought back, (2) SUMMARIZE the picture so far ('So we have: event X, you felt Y, you thought Z'), (3) Then ask about action. DON'T jump immediately! Even if thought is not vulnerable - give it a moment. If thought IS harsh/vulnerable ('I'm not worthy', 'אני לא ראוי') - acknowledge weight before moving. See Examples 4.5 and 4.7.",
            "S5": "Action & Desired stage: Two-part stage. BEFORE asking about action, you can briefly explain WHY we're doing this (see Example 2.5) - we're building the full picture of what happened (emotion-thought-action) to understand the gap. Don't explain EVERY time, only when it feels natural. If user gave both parts (action + desired), move to S6. If missing a part, request it.",
            "S6": "Gap stage: Now that you have the current (event+emotions+thought+action) and desired, help user identify the gap and name it + rate 1-10. CRITICAL: If user gives a rating (e.g. '5') - don't interpret it! ❌ Don't say 'your rating was 5 in the meeting'. ✅ Simply accept the rating and ask for the gap name or move to next stage. DON'T INTERPRET! Don't ask for event again!",
            "S7": "Pattern stage: Help identify recurring pattern and belief (paradigm).",
            "S8": "Stance stage: Help identify profit AND loss from their stance. Ask: What do you gain? What do you lose? Simple profit/loss table.",
            "S9": "Forces stage (KaMaZ): Identify source forces (values, beliefs) and nature forces (skills, abilities). This is their Core Essence Card.",
            "S11": "Renewal & Choice stage: Help user choose new stance/paradigm/pattern. This is their New Floor.",
            "S12": "Vision stage: Help user see the big picture - mission, destiny, heart's desire. Beyond one event.",
            "S10": "Commitment stage: Build commitment with full formula (difficulty + source/nature + result).",
        }
    
    return guidance.get(stage, "המשך את השיחה" if language == "he" else "Continue conversation")


# Public API
__all__ = ["generate_natural_response"]

