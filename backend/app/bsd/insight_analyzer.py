"""
Insight Analyzer - Deep psychological analysis of user responses.

This component runs AFTER routing (doesn't affect stage transitions)
but BEFORE conversational_coach generates response.

Purpose: Provide coaching insights to improve conversation quality:
- Detect shallow/superficial engagement
- Identify emotional incongruence (mismatched emotions)
- Highlight dominant emotions that need exploration
- Suggest when to deepen vs. move forward

This is NOT a gatekeeper - it's a coach assistant!
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
import logging
import re

from .state_schema import BsdState
from .llm import get_azure_chat_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


class EngagementQuality(str, Enum):
    """Quality of user's engagement in the conversation."""
    DEEP = "deep"  # Long, detailed, vulnerable sharing
    MODERATE = "moderate"  # Adequate responses
    SHALLOW = "shallow"  # Short, terse, surface-level
    AVOIDANT = "avoidant"  # Deflecting, vague, resistant


class EmotionalCongruence(str, Enum):
    """Match between event tone and emotions shared."""
    CONGRUENT = "congruent"  # Emotions match event (sad for loss)
    INCONGRUENT = "incongruent"  # Mismatch (happy for tragedy)
    UNCLEAR = "unclear"  # Can't determine from context


class InsightType(str, Enum):
    """Type of coaching insight."""
    SHALLOW_RESPONSE = "shallow_response"
    EMOTIONAL_MISMATCH = "emotional_mismatch"
    DOMINANT_EMOTION = "dominant_emotion"
    MINIMIZED_EMOTION = "minimized_emotion"
    UNEXPLORED_DEPTH = "unexplored_depth"
    AVOIDANCE_PATTERN = "avoidance_pattern"
    CUMULATIVE_PATTERN = "cumulative_pattern"  # User talking about pattern, not specific event
    VULNERABILITY_MOMENT = "vulnerability_moment"
    EXTERNAL_ATTRIBUTION = "external_attribution"  # User quoting what others say (not their own desire)


class CoachingInsight(BaseModel):
    """A single insight about the user's response."""
    type: InsightType
    severity: float = Field(ge=0.0, le=1.0, description="How important is this? 0=minor, 1=critical")
    observation: str = Field(description="What did we notice?")
    interpretation: str = Field(description="What might this mean?")
    suggestion: str = Field(description="What should the coach do?")
    relevant_text: Optional[str] = Field(None, description="Specific text that triggered this")


class InsightAnalysis(BaseModel):
    """Complete analysis of user's response."""
    engagement_quality: EngagementQuality
    emotional_congruence: EmotionalCongruence
    depth_score: float = Field(ge=0.0, le=10.0, description="Overall depth (0=surface, 10=breakthrough)")
    insights: List[CoachingInsight] = Field(default_factory=list)
    summary: str = Field(description="One-sentence summary for conversational_coach")


class InsightAnalyzer:
    """Analyzes user responses for coaching insights."""
    
    def __init__(self):
        self.llm = None
    
    async def analyze(
        self,
        user_message: str,
        stage: str,
        language: str,
        state: BsdState
    ) -> InsightAnalysis:
        """
        Main analysis function.
        
        Args:
            user_message: User's current message
            stage: Current coaching stage
            language: "he" or "en"
            state: Current BSD state (for context)
        
        Returns:
            InsightAnalysis with insights and guidance
        """
        insights = []
        
        # 0. Check for external attribution (critical for S1)
        # IMPORTANT: Check this FIRST before anything else!
        # "אשתי אומרת שאני לא רומנטי" = external attribution, not user's own desire!
        if stage == "S1":
            external_insight = self._detect_external_attribution(user_message, state, language)
            if external_insight:
                insights.append(external_insight)
        
        # 1. Check engagement quality (shallow vs deep)
        engagement, shallow_insight = self._analyze_engagement_quality(user_message, language)
        if shallow_insight:
            insights.append(shallow_insight)
        
        # 1.5. Check for cumulative pattern (especially important for S2)
        if stage == "S2":
            pattern_insight = self._detect_cumulative_pattern(user_message, state, language)
            if pattern_insight:
                insights.append(pattern_insight)
        
        # 2. Check emotional congruence (for S3 stage)
        if stage == "S3":
            congruence, mismatch_insight = await self._analyze_emotional_congruence(
                user_message, state, language
            )
        else:
            congruence = EmotionalCongruence.UNCLEAR
            mismatch_insight = None
        
        if mismatch_insight:
            insights.append(mismatch_insight)
        
        # 3. Analyze emotions for dominance/minimization (for S3 stage)
        if stage == "S3":
            emotion_insights = self._analyze_emotion_hierarchy(user_message, language)
            insights.extend(emotion_insights)
        
        # 4. Check for vulnerable moments that need space (for S4 stage)
        if stage == "S4":
            vulnerable_insight = self._analyze_thought_depth(user_message, language)
            if vulnerable_insight:
                insights.append(vulnerable_insight)
        
        # 5. Calculate overall depth score
        depth_score = self._calculate_depth_score(user_message, insights, stage)
        
        # 6. Generate summary for conversational_coach
        summary = self._generate_summary(engagement, insights, language)
        
        return InsightAnalysis(
            engagement_quality=engagement,
            emotional_congruence=congruence,
            depth_score=depth_score,
            insights=insights,
            summary=summary
        )
    
    def _analyze_engagement_quality(
        self,
        user_message: str,
        language: str
    ) -> Tuple[EngagementQuality, Optional[CoachingInsight]]:
        """
        Detect if user is being superficial/shallow.
        
        Shallow indicators:
        - Very short responses (< 5 words)
        - Single words ("כעס", "נורא")
        - Vague responses ("לא יודע", "זה מסובך")
        """
        words = user_message.strip().split()
        word_count = len(words)
        
        # Very short response
        if word_count <= 2:
            if language == "he":
                observation = f"תשובה קצרה מאוד: '{user_message}' (רק {word_count} מילים)"
                interpretation = "המתאמן נותן תשובות מינימליסטיות - אולי מתגונן, לא בטוח, או לא מבין מה מצפים ממנו"
                suggestion = "אל תקבל תשובה קצרה. שאל: 'ספר לי יותר על זה' או 'מה עוד היה שם?'"
            else:
                observation = f"Very short response: '{user_message}' (only {word_count} words)"
                interpretation = "User giving minimal answers - might be defensive, unsure, or doesn't understand what's expected"
                suggestion = "Don't accept short answer. Ask: 'Tell me more about that' or 'What else was there?'"
            
            return EngagementQuality.SHALLOW, CoachingInsight(
                type=InsightType.SHALLOW_RESPONSE,
                severity=0.7,
                observation=observation,
                interpretation=interpretation,
                suggestion=suggestion,
                relevant_text=user_message
            )
        
        # Short but not critical
        elif word_count <= 5:
            if language == "he":
                observation = f"תשובה קצרה: {word_count} מילים"
                suggestion = "נסה לפתוח: 'תוכל להרחיב?'"
            else:
                observation = f"Short response: {word_count} words"
                suggestion = "Try to open up: 'Can you elaborate?'"
            
            return EngagementQuality.MODERATE, CoachingInsight(
                type=InsightType.SHALLOW_RESPONSE,
                severity=0.4,
                observation=observation,
                interpretation="Response is brief but acceptable",
                suggestion=suggestion,
                relevant_text=user_message
            )
        
        # Check for vague patterns
        vague_patterns_he = ["לא יודע", "זה מסובך", "קשה להסביר", "לא זכור", "לא בטוח"]
        vague_patterns_en = ["don't know", "it's complicated", "hard to explain", "don't remember", "not sure"]
        patterns = vague_patterns_he if language == "he" else vague_patterns_en
        
        if any(pattern in user_message.lower() for pattern in patterns):
            if language == "he":
                observation = "תשובה מתחמקת/לא ברורה"
                interpretation = "המתאמן נמנע מלהיכנס לעומק - אולי לא נוח, לא בטוח, או צריך עזרה להגדיר"
                suggestion = "עזור לו להגדיר: תן דוגמה, שאל שאלה ספציפית יותר"
            else:
                observation = "Vague/avoidant response"
                interpretation = "User avoiding depth - might be uncomfortable, unsure, or needs help defining"
                suggestion = "Help them define: give example, ask more specific question"
            
            return EngagementQuality.AVOIDANT, CoachingInsight(
                type=InsightType.AVOIDANCE_PATTERN,
                severity=0.6,
                observation=observation,
                interpretation=interpretation,
                suggestion=suggestion,
                relevant_text=user_message
            )
        
        # Adequate engagement
        if word_count >= 15:
            return EngagementQuality.DEEP, None
        else:
            return EngagementQuality.MODERATE, None
    
    async def _analyze_emotional_congruence(
        self,
        user_message: str,
        state: BsdState,
        language: str
    ) -> Tuple[EmotionalCongruence, Optional[CoachingInsight]]:
        """
        Check if emotions match the event tone.
        
        Examples of INCONGRUENCE:
        - Event: "אבא שלי נפטר" + Emotions: "שמח, מאושר"
        - Event: "קיבלתי עליה" + Emotions: "עצב, יאוש"
        """
        # Get event description from state
        # Note: Event description is stored in last_user_message when S2 is answered,
        # not in EventActual. For now, skip congruence check if we can't get event context.
        if not state.cognitive_data or not state.last_user_message:
            return EmotionalCongruence.UNCLEAR, None
        
        # Try to extract event context from conversation history or last_user_message
        # For simplicity, skip if we don't have enough context
        event_desc = state.last_user_message or ""
        if len(event_desc) < 10:
            return EmotionalCongruence.UNCLEAR, None
        
        # Extract emotions from user message
        emotions_in_message = user_message.strip()
        
        # Use LLM to judge congruence
        try:
            if not self.llm:
                self.llm = get_azure_chat_llm(purpose="reasoner")
            
            prompt = f"""You are analyzing emotional congruence in a coaching conversation.

EVENT: "{event_desc}"
EMOTIONS SHARED: "{emotions_in_message}"

Question: Do the emotions MATCH the event tone?

Examples of CONGRUENT:
- Event: "אבא שלי נפטר" + Emotions: "עצב, יאוש, כעס"
- Event: "קיבלתי עליה" + Emotions: "שמחה, התרגשות"

Examples of INCONGRUENT (RED FLAGS):
- Event: "אבא שלי נפטר" + Emotions: "שמח, מאושר" ← Positive for tragedy!
- Event: "הצלחתי בפרויקט" + Emotions: "עצב, יאוש" ← Negative for success!

Respond ONLY with JSON:
{{"congruent": true/false, "reason": "brief explanation"}}"""
            
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a precise evaluator. Output only valid JSON."),
                HumanMessage(content=prompt)
            ])
            
            # Parse response
            import json
            response_text = response.content.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            is_congruent = result.get("congruent", True)
            reason = result.get("reason", "")
            
            if not is_congruent:
                logger.warning(f"⚠️ [EMOTIONAL MISMATCH] {reason}")
                
                if language == "he":
                    observation = f"אי-התאמה רגשית: {emotions_in_message}"
                    interpretation = f"הרגשות לא מתאימים לאירוע. {reason}. זה יכול להיות הכחשה, הימנעות, או משהו מורכב יותר."
                    suggestion = "בדוק בעדינות: 'שמח? זה מפתיע לי בהתחשב במה שקרה. ספר לי יותר...'"
                else:
                    observation = f"Emotional mismatch: {emotions_in_message}"
                    interpretation = f"Emotions don't match event. {reason}. Could be denial, avoidance, or complexity."
                    suggestion = "Gently probe: 'Happy? That surprises me given what happened. Tell me more...'"
                
                return EmotionalCongruence.INCONGRUENT, CoachingInsight(
                    type=InsightType.EMOTIONAL_MISMATCH,
                    severity=0.9,  # High severity - this is important!
                    observation=observation,
                    interpretation=interpretation,
                    suggestion=suggestion,
                    relevant_text=emotions_in_message
                )
            
            return EmotionalCongruence.CONGRUENT, None
            
        except Exception as e:
            logger.error(f"[CONGRUENCE CHECK ERROR] {e}")
            return EmotionalCongruence.UNCLEAR, None
    
    def _analyze_emotion_hierarchy(
        self,
        user_message: str,
        language: str
    ) -> List[CoachingInsight]:
        """
        Identify dominant vs. minimized emotions.
        
        Dominance markers (Hebrew):
        - Intensity: "כעס עז", "תסכול גדול", "עצב עמוק"
        - Repetition: "כעס ועוד כעס"
        - Position: First emotion mentioned
        
        Minimization markers (Hebrew):
        - Diminishers: "קצת עצב", "מעט פחד", "גם היה..."
        - Hedging: "אולי", "כנראה"
        - Position: Last, as afterthought
        """
        insights = []
        
        # Hebrew intensity markers
        intensity_markers = ["עז", "חזק", "גדול", "עמוק", "רב", "נורא"]
        diminisher_markers = ["קצת", "מעט", "גם", "קצת", "מעט"]
        
        # Find emotions with markers
        # Clean words: remove punctuation
        import string
        words = [w.strip(string.punctuation) for w in user_message.split()]
        
        for i, word in enumerate(words):
            # Check for emotion + intensity (e.g., "כעס עז")
            if i < len(words) - 1:
                next_word = words[i + 1]
                if next_word in intensity_markers:
                    if language == "he":
                        observation = f"רגש דומיננטי זוהה: '{word} {next_word}'"
                        interpretation = f"המתאמן הדגיש את '{word}' באופן מיוחד. זה הרגש המרכזי."
                        suggestion = f"התמקד ב'{word}' קודם, זה הכי חזק. אח\"כ חזור לרגשות אחרים."
                    else:
                        observation = f"Dominant emotion detected: '{word} {next_word}'"
                        interpretation = f"User emphasized '{word}' specifically. This is the core emotion."
                        suggestion = f"Focus on '{word}' first, it's strongest. Return to other emotions later."
                    
                    insights.append(CoachingInsight(
                        type=InsightType.DOMINANT_EMOTION,
                        severity=0.7,
                        observation=observation,
                        interpretation=interpretation,
                        suggestion=suggestion,
                        relevant_text=f"{word} {next_word}"
                    ))
            
            # Check for diminisher + emotion (e.g., "קצת עצב")
            if i < len(words) - 1:
                next_word = words[i + 1]
                if word in diminisher_markers:
                    if language == "he":
                        observation = f"רגש ממוזער זוהה: '{word} {next_word}'"
                        interpretation = f"המתאמן ממזער את '{next_word}'. למה? הגנה? לא נוח?"
                        suggestion = f"אחרי שעברת על הרגשות האחרים, חזור: 'ואת ה{next_word}? למה '{word}'?'"
                    else:
                        observation = f"Minimized emotion detected: '{word} {next_word}'"
                        interpretation = f"User is minimizing '{next_word}'. Why? Defense? Discomfort?"
                        suggestion = f"After other emotions, circle back: 'And the {next_word}? Why '{word}'?'"
                    
                    insights.append(CoachingInsight(
                        type=InsightType.MINIMIZED_EMOTION,
                        severity=0.6,
                        observation=observation,
                        interpretation=interpretation,
                        suggestion=suggestion,
                        relevant_text=f"{word} {next_word}"
                    ))
        
        return insights
    
    def _analyze_thought_depth(
        self,
        user_message: str,
        language: str
    ) -> Optional[CoachingInsight]:
        """
        Check if thought (S4) needs more exploration.
        
        Example:
        User: "חשבתי שאני לא מספיק"
        → This is deep but BRIEF. What does "not enough" mean?
        """
        word_count = len(user_message.split())
        
        # Vulnerability markers
        vulnerable_markers_he = ["לא מספיק", "לא ראוי", "אפס", "כישלון", "פגום", "לא טוב"]
        vulnerable_markers_en = ["not enough", "not worthy", "worthless", "failure", "broken", "not good"]
        
        markers = vulnerable_markers_he if language == "he" else vulnerable_markers_en
        has_vulnerable_content = any(marker in user_message.lower() for marker in markers)
        
        if has_vulnerable_content and word_count < 10:
            if language == "he":
                observation = f"מחשבה עמוקה אבל קצרה: '{user_message}'"
                interpretation = "המתאמן שיתף משהו משמעותי אבל לא פירט. מה בדיוק הוא מתכוון?"
                suggestion = "אל תמהר לפעולה. שאל: 'לא מספיק... למה? לא מספיק טוב? חכם? ראוי? מה?'"
            else:
                observation = f"Deep thought but brief: '{user_message}'"
                interpretation = "User shared something significant but didn't elaborate. What exactly does it mean?"
                suggestion = "Don't rush to action. Ask: 'Not enough... in what way? Not good enough? Smart enough? What?'"
            
            return CoachingInsight(
                type=InsightType.UNEXPLORED_DEPTH,
                severity=0.8,
                observation=observation,
                interpretation=interpretation,
                suggestion=suggestion,
                relevant_text=user_message
            )
        
        return None
    
    def _detect_cumulative_pattern(
        self,
        user_message: str,
        state: BsdState,
        language: str
    ) -> Optional[CoachingInsight]:
        """
        Detect when user is describing a PATTERN (cumulative, ongoing)
        instead of a SPECIFIC EVENT.
        
        CRITICAL for S2 (Event stage):
        - If topic is relational (זוגיות, משפחה, עבודה) + user says "always", "every time", "accumulated"
        - Need to first clarify CONTEXT before asking for event
        
        Example:
        Topic: "זוגיות"
        User: "זה לא רגע, זה נסיון מצטבר"
        → Don't just repeat "tell me about a moment"!
        → First ask: "האם יש לך קשר זוגי כרגע? או שהיה לאחרונה?"
        """
        msg = user_message.lower()
        
        # Pattern markers (Hebrew & English)
        pattern_markers_he = [
            "תמיד", "כל פעם", "כל הזמן", "בדרך כלל", "לרוב",
            "מצטבר", "נסיון מצטבר", "זה לא רגע", "לא רגע", "לא בדיוק רגע",
            "זה דפוס", "זה קורה הרבה", "זה חוזר", "זה נמשך",
            "זה לא משהו ספציפי", "לא משהו ספציפי", "זה כללי"
        ]
        pattern_markers_en = [
            "always", "every time", "usually", "generally", "typically",
            "cumulative", "it's not a moment", "it's a pattern",
            "this happens a lot", "this keeps happening", "this continues"
        ]
        
        markers = pattern_markers_he if language == "he" else pattern_markers_en
        is_pattern = any(marker in msg for marker in markers)
        
        if not is_pattern:
            return None
        
        # Check if topic is relational (needs context clarification)
        topic = state.cognitive_data.topic if state.cognitive_data else ""
        relational_topics_he = ["זוגיות", "משפחה", "הורות", "עבודה", "קשר", "חברות"]
        relational_topics_en = ["relationship", "romance", "family", "parenting", "work", "friendship"]
        
        relational_topics = relational_topics_he if language == "he" else relational_topics_en
        is_relational = any(rel in topic.lower() for rel in relational_topics) if topic else False
        
        if is_relational:
            # High severity - need to change approach!
            if language == "he":
                observation = f"דפוס מצטבר + נושא רלציוני ('{topic}')"
                interpretation = "המתאמן מדבר על דפוס, לא אירוע ספציפי. בנושאים רלציוניים, צריך קודם לברר הקשר!"
                suggestion = f"אל תבקש 'רגע מהשבוע האחרון' מיד! קודם ברר: האם יש לך {topic} כרגע? או שהיה לאחרונה? אחר כך תבקש דוגמה מתוך הקשר הזה."
            else:
                observation = f"Cumulative pattern + relational topic ('{topic}')"
                interpretation = "User is describing a pattern, not a specific event. For relational topics, clarify context first!"
                suggestion = f"Don't ask for 'a moment from last week' yet! First clarify: Do you have a {topic} currently? Or did you recently? Then ask for an example from that context."
            
            return CoachingInsight(
                type=InsightType.CUMULATIVE_PATTERN,
                severity=0.9,  # HIGH - requires approach change!
                observation=observation,
                interpretation=interpretation,
                suggestion=suggestion,
                relevant_text=user_message
            )
        else:
            # Non-relational pattern - still useful to note
            if language == "he":
                observation = "דפוס מצטבר (לא אירוע ספציפי)"
                interpretation = "המתאמן מדבר על דפוס כללי. צריך לבקש דוגמה ספציפית."
                suggestion = "אל תחזור על אותה שאלה! נסה: 'אני מבין שזה דפוס. בוא ניקח דוגמה אחת - ספר לי על פעם אחת לאחרונה שזה קרה.'"
            else:
                observation = "Cumulative pattern (not specific event)"
                interpretation = "User is describing a general pattern. Need to ask for specific example."
                suggestion = "Don't repeat the same question! Try: 'I understand it's a pattern. Let's take one example - tell me about one recent time this happened.'"
            
            return CoachingInsight(
                type=InsightType.CUMULATIVE_PATTERN,
                severity=0.7,
                observation=observation,
                interpretation=interpretation,
                suggestion=suggestion,
                relevant_text=user_message
            )
    
    def _detect_external_attribution(
        self,
        user_message: str,
        state: BsdState,
        language: str
    ) -> Optional[CoachingInsight]:
        """
        Detect when user is quoting OTHERS instead of expressing THEIR OWN desire.
        
        CRITICAL for S1 (Topic stage):
        - User says "My wife says I'm not romantic" / "אשתי אומרת שאני לא רומנטי"
        - This is NOT the user's own coaching topic!
        - Need to clarify: What do YOU want? Not what others say!
        
        Example:
        User: "אשתי אומרת שאני לא רומנטי"
        Coach: ❌ "ספר על רגע אחד לאחרונה..."
        Coach: ✅ "אוקיי, אני שומע שאשתך אומרת שאתה לא רומנטי.
                   אבל מה **אתה** רוצה? על מה **אתה** רוצה להתאמן?"
        """
        msg = user_message.lower()
        
        # External attribution markers (Hebrew & English)
        external_markers_he = [
            "אמר לי", "אמרה לי", "אמרו לי",
            "אומר לי", "אומרת לי", "אומרים לי",
            "אשתי אומרת", "בעלי אומר", "המנהל שלי אומר",
            "חברים שלי אומרים", "המשפחה שלי אומרת",
            "אמרו שאני", "אומרים שאני", "נאמר לי",
            "קיבלתי פידבק", "קיבלתי ביקורת"
        ]
        external_markers_en = [
            "my wife says", "my husband says", "my boss says",
            "my friends say", "my family says", "people tell me",
            "i was told", "they say", "someone said",
            "i got feedback", "i received criticism"
        ]
        
        markers = external_markers_he if language == "he" else external_markers_en
        is_external = any(marker in msg for marker in markers)
        
        if not is_external:
            return None
        
        # Check if we're in S1 (topic selection) - this is CRITICAL there!
        current_stage = state.current_state if state else ""
        severity = 0.95 if current_stage == "S1" else 0.7
        
        if language == "he":
            observation = "ציטוט של מה שאחרים אומרים (לא רצון אישי)"
            interpretation = "המתאמן מספר מה **אחרים** אומרים עליו, לא מה **הוא** רוצה לשנות!"
            suggestion = (
                "⚠️ ACTION: אל תעבור ל-S2 עדיין! זה לא נושא אימון ברור!\n"
                "אמור משהו כמו: 'אוקיי, אני שומע שאשתך/בעלך/הבוס אומר X.\n"
                "אבל מה **אתה** רוצה? על מה **אתה** רוצה להתאמן?'\n"
                "נשאר ב-S1 עד שהמתאמן מביע רצון אישי!"
            )
        else:
            observation = "Quoting what others say (not personal desire)"
            interpretation = "User is telling what **others** say about them, not what **they** want to change!"
            suggestion = (
                "⚠️ ACTION: Don't move to S2 yet! This is not a clear coaching topic!\n"
                "Say something like: 'Okay, I hear that your wife/husband/boss says X.\n"
                "But what do **you** want? What do **you** want to work on?'\n"
                "Stay in S1 until user expresses their own desire!"
            )
        
        return CoachingInsight(
            type=InsightType.EXTERNAL_ATTRIBUTION,
            severity=severity,
            observation=observation,
            interpretation=interpretation,
            suggestion=suggestion,
            relevant_text=user_message
        )
    
    def _calculate_depth_score(
        self,
        user_message: str,
        insights: List[CoachingInsight],
        stage: str
    ) -> float:
        """
        Calculate overall depth score (0-10).
        
        Factors:
        - Length (longer = more sharing)
        - Vulnerability (harsh self-thoughts = deep)
        - Insights severity (high severity issues = lower depth)
        """
        word_count = len(user_message.split())
        
        # Base score from length
        if word_count <= 5:
            base_score = 2.0
        elif word_count <= 10:
            base_score = 4.0
        elif word_count <= 20:
            base_score = 6.0
        else:
            base_score = 8.0
        
        # Penalize for severe issues
        penalty = 0.0
        for insight in insights:
            if insight.severity >= 0.7:
                penalty += 1.5
            elif insight.severity >= 0.5:
                penalty += 0.5
        
        # Bonus for vulnerability (if no mismatch)
        has_mismatch = any(i.type == InsightType.EMOTIONAL_MISMATCH for i in insights)
        vulnerable_markers_he = ["לא מספיק", "לא ראוי", "אפס", "כישלון", "אני לא טוב"]
        has_vulnerable = any(marker in user_message.lower() for marker in vulnerable_markers_he)
        
        if has_vulnerable and not has_mismatch:
            base_score += 2.0
        
        final_score = max(0.0, min(10.0, base_score - penalty))
        return final_score
    
    def _generate_summary(
        self,
        engagement: EngagementQuality,
        insights: List[CoachingInsight],
        language: str
    ) -> str:
        """Generate one-sentence summary for conversational_coach."""
        if not insights:
            if language == "he":
                return "תשובה תקינה, אין התראות מיוחדות."
            else:
                return "Response is adequate, no special alerts."
        
        # Prioritize by severity
        top_insight = max(insights, key=lambda x: x.severity)
        
        if language == "he":
            return f"⚠️ {top_insight.observation}. {top_insight.suggestion}"
        else:
            return f"⚠️ {top_insight.observation}. {top_insight.suggestion}"


# Public API
async def analyze_response(
    user_message: str,
    stage: str,
    language: str,
    state: BsdState
) -> InsightAnalysis:
    """
    Main entry point for insight analysis.
    
    Usage in conversational_coach:
    ```python
    analysis = await analyze_response(user_message, stage, language, state)
    if analysis.depth_score < 4.0:
        # Add guidance to system prompt
        system_prompt += f"\n\n🔍 INSIGHT ALERT:\n{analysis.summary}"
    ```
    """
    analyzer = InsightAnalyzer()
    return await analyzer.analyze(user_message, stage, language, state)


__all__ = [
    "InsightAnalyzer",
    "InsightAnalysis",
    "CoachingInsight",
    "EngagementQuality",
    "EmotionalCongruence",
    "InsightType",
    "analyze_response"
]

