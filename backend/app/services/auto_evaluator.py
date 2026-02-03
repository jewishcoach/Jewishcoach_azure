"""
LLM-as-a-Judge Quality Auditing System

This service asynchronously evaluates Coach responses for methodology compliance
WITHOUT impacting user experience latency.
"""

from openai import AzureOpenAI
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import os
import json
from ..bsd.stage_defs import STAGES

class QualityJudge:
    """
    Asynchronous quality auditor that checks Coach responses against
    strict PDF methodology rules.
    
    Uses gpt-4o for accuracy in detecting subtle methodology violations.
    """
    
    def __init__(self):
        """Initialize the Quality Judge with Azure OpenAI client"""
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        # Use standard gpt-4o for better accuracy in quality checks
        self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        
        # Build valid stage names list for prompt (single source of truth: BSD core)
        self.valid_stages_he = [s.name_he for s in STAGES.values()]
        self.valid_stages_en = [s.name_en for s in STAGES.values()]
    
    async def evaluate_response(
        self,
        conversation_history: List[Dict],
        current_stage: str,
        latest_bot_response: str,
        db: Session
    ) -> Optional[Dict]:
        """
        Evaluate Coach response for methodology compliance.
        
        Args:
            conversation_history: Recent chat history
            current_stage: Current coaching stage
            latest_bot_response: The Coach's latest message to audit
            db: Database session (not used in evaluation, but available)
        
        Returns:
            Dict with flag data if issue found, None if compliant
            {
                "is_compliant": bool,
                "issue_type": str,
                "reasoning": str,
                "severity": str
            }
        """
        
        # Build conversation context (last 4 messages for context)
        recent_messages = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
        conversation_text = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Coach'}: {msg['content']}"
            for msg in recent_messages
        ])
        
        stage_he = STAGES.get(current_stage).name_he if current_stage in STAGES else current_stage
        # Build the Judge prompt with strict Ground Truth rules
        judge_prompt = f"""You are a QA Auditor for a Jewish Coaching methodology based on a strict 11-stage process.
Your task is to review the Coach's latest response and detect ANY violations of the methodology.

**VALID STAGES (The ONLY acceptable stage names):**
Hebrew: {', '.join(self.valid_stages_he)}
English: {', '.join(self.valid_stages_en)}

**CURRENT STAGE:** {current_stage} ({stage_he})

**CONVERSATION CONTEXT:**
{conversation_text}

**COACH'S LATEST RESPONSE TO AUDIT:**
"{latest_bot_response}"

**STRICT GROUND TRUTH RULES:**

1. **Stage Integrity Check:**
   - Did the coach mention ANY stage name that is NOT in the valid stages list above?
   - Examples of VIOLATIONS: "Definition Stage", "Solution Stage", "Clarification Phase", "Next Step"
   - This is a CRITICAL FAIL → issue_type: "Hallucination", severity: "High"

2. **Methodology Check:**
   - Did the coach give advice, instructions, or tell the client what to do?
   - The coach should ONLY ask questions (Socratic method)
   - Examples of VIOLATIONS: "You should...", "Try doing...", "I suggest...", "What you need to do is..."
   - This is a FAIL → issue_type: "Advice", severity: "Medium"

3. **Gap Phase Logic Check (ONLY if current_stage is 'Gap'):**
   - The Gap stage requires THREE parts: (a) Current Reality, (b) Desired Reality, (c) Opportunity Question
   - Did the coach declare the Gap stage complete or move to next stage WITHOUT asking "Are you willing to see this as an opportunity?" or equivalent?
   - This is a FAIL → issue_type: "Logic Error", severity: "High"

4. **Announcement Check:**
   - Did the coach explicitly announce stage transitions like "Let's move to the next stage" or "We're now in the Pattern stage"?
   - The coach should transition naturally through questions, not announcements
   - This is a FAIL → issue_type: "Methodology", severity: "Low"

**RESPOND IN JSON FORMAT:**
{{
    "is_compliant": true/false,
    "issue_type": "Hallucination" | "Advice" | "Logic Error" | "Methodology" | null,
    "reasoning": "Brief explanation of the issue found (or empty if compliant)",
    "severity": "High" | "Medium" | "Low" | null
}}

**IMPORTANT:**
- If NO violations are found, return {{"is_compliant": true, "issue_type": null, "reasoning": "", "severity": null}}
- If ANY violation is found, return {{"is_compliant": false, ...}} with details
- Be strict but fair - only flag actual violations, not minor stylistic choices
"""
        
        try:
            # Call the Judge LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a strict quality auditor. Be thorough and unbiased in your evaluation."},
                    {"role": "user", "content": judge_prompt}
                ],
                temperature=0.2,  # Low temperature for consistent binary decisions
                max_tokens=200,   # Judge only needs to return simple JSON
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # Log the evaluation
            print(f"\n🔍 JUDGE EVALUATION: Stage '{current_stage}'")
            print(f"   ✓ Compliant: {result.get('is_compliant', True)}")
            
            if not result.get("is_compliant", True):
                print(f"   ⚠️  Issue Type: {result.get('issue_type')}")
                print(f"   ⚠️  Severity: {result.get('severity')}")
                print(f"   ⚠️  Reasoning: {result.get('reasoning')}")
                
                # Return flag data (None values will be filtered out by caller)
                return {
                    "issue_type": result.get("issue_type", "Unknown"),
                    "reasoning": result.get("reasoning", "No reasoning provided"),
                    "severity": result.get("severity", "Medium")
                }
            else:
                print(f"   ✅ No issues detected")
                return None
                
        except Exception as e:
            print(f"❌ JUDGE ERROR: {e}")
            import traceback
            traceback.print_exc()
            # Don't crash on judge errors - just log and continue
            return None


