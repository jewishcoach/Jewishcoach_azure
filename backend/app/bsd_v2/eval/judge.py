"""
LLM-as-judge for BSD coaching transcripts (offline evaluation — never in the request path).

Judge = Claude on Amazon Bedrock (a different model family from the gpt-4o-mini coach, so it doesn't favour
the coach's own style). The rubric (rubric.md, grounded in the BSD book + booklet + redesign synthesis) is the
cached system prompt; the transcript is the user message; output is validated against JudgeReport.
"""

import json
import os
from pathlib import Path
from typing import Any

import anthropic
from pydantic import BaseModel
from sqlalchemy import create_engine, text

RUBRIC_PATH = Path(__file__).with_name("rubric.md")
JUDGE_MODEL = os.getenv("BSD_JUDGE_MODEL", "anthropic.claude-opus-5-5")
JUDGE_REGION = os.getenv("BSD_JUDGE_AWS_REGION", os.getenv("AWS_REGION", "us-east-1"))


# ── output schema (mirrors rubric §4) ─────────────────────────────────────────

# Scores are 1-5; 0 = N/A. (No Optional/unions: they blow up the structured-output grammar.)
class TurnScores(BaseModel):
    D1_method: int
    D2_client_words: int
    D3_no_spoonfeed: int
    D4_enabling_q: int
    D5_one_question: int
    D6_reflect_once: int
    D7_warmth: int
    D8_hebrew_gender: int
    D9_hidden_mechanics: int
    D10_pacing: int
    D11_safety: int


class TurnJudgement(BaseModel):
    turn: int
    stage: str
    scores: TurnScores
    hard_fails: list[str]
    turn_score: int
    note: str


class StageJudgement(BaseModel):
    stage: str
    passed: bool
    gate_met: bool
    coach_turns: int
    over_budget: bool
    failure_modes: list[str]
    deepening_correct: bool
    evidence: str


class FatigueSignal(BaseModel):
    turn: int
    signal: str


class ConversationJudgement(BaseModel):
    W1_insight_own_words: int
    W2_real_choice: int
    W3_economy_fatigue: int
    W4_arc_coherence: int
    W5_agency: int
    total_coach_chat_turns: int
    fatigue_signals: list[FatigueSignal]
    overall: int


class Issue(BaseModel):
    rank: int
    turns: list[int]
    dimension: str
    stage: str
    issue: str
    fix: str


class JudgeReport(BaseModel):
    turns: list[TurnJudgement]
    stages: list[StageJudgement]
    conversation: ConversationJudgement
    top_issues: list[Issue]


# ── transcripts ───────────────────────────────────────────────────────────────

def load_transcript(database_url: str, conversation_id: int | None = None) -> tuple[int, list[dict[str, Any]]]:
    """Messages of one conversation (latest if not given) as numbered turns."""
    engine = create_engine(database_url)
    with engine.connect() as conn:
        if conversation_id is None:
            conversation_id = conn.execute(text("select conversation_id from messages order by id desc limit 1")).scalar()
        rows = conn.execute(
            text("select role, content, meta from messages where conversation_id = :c order by id"),
            {"c": conversation_id},
        ).fetchall()
    turns = []
    for i, (role, content, meta) in enumerate(rows, 1):
        meta = json.loads(meta) if isinstance(meta, str) else (meta or {})
        turns.append({
            "turn": i,
            "speaker": "coach" if role == "assistant" else "client",
            "stage": meta.get("phase"),
            "card": meta.get("tool_type") if meta.get("tool_submission") else None,
            "safety": meta.get("safety"),
            "text": content,
        })
    return conversation_id, turns


def format_transcript(turns: list[dict[str, Any]]) -> str:
    lines = []
    for t in turns:
        tag = f"[{t['turn']}] {'COACH' if t['speaker'] == 'coach' else 'CLIENT'}"
        if t["stage"]:
            tag += f" current_step={t['stage']}"
        if t["card"]:
            tag += f" (card submission: {t['card']})"
        if t["safety"]:
            tag += f" (system safety response: {t['safety']})"
        lines.append(f"{tag}\n{t['text']}")
    return "\n\n".join(lines)


# ── judging ───────────────────────────────────────────────────────────────────

class JudgeRefused(RuntimeError):
    pass


def judge_transcript(turns: list[dict[str, Any]], persona_note: str = "") -> tuple[JudgeReport, dict[str, Any]]:
    client = anthropic.AnthropicBedrockMantle(aws_region=JUDGE_REGION).with_options(timeout=900.0)
    rubric = RUBRIC_PATH.read_text(encoding="utf-8")
    instructions = (
        "Judge the following coaching transcript strictly by the rubric in the system prompt. "
        "Score only COACH turns in `turns`. Use the stage tags as given. "
        "Safety responses tagged '(system safety response)' are fixed system messages — judge only whether they "
        "were triggered appropriately (D11), not their wording. "
        "All free-text fields (note, evidence, issue, fix) may be in Hebrew or English; keep them short. "
        "Use 0 for any score that is N/A (instead of null); deepening_correct=true when no check failed."
    )
    if persona_note:
        instructions += f"\nContext about the (simulated) client: {persona_note}"
    response = client.messages.parse(
        model=JUDGE_MODEL,
        max_tokens=32000,
        output_config={"effort": "high"},
        system=[{"type": "text", "text": rubric, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"{instructions}\n\n<transcript>\n{format_transcript(turns)}\n</transcript>"}],
        output_format=JudgeReport,
    )
    if response.stop_reason == "refusal":
        raise JudgeRefused(f"judge refused: {getattr(response.stop_details, 'category', None)}")
    usage = {
        "input_tokens": response.usage.input_tokens,
        "cache_read_input_tokens": response.usage.cache_read_input_tokens,
        "cache_creation_input_tokens": response.usage.cache_creation_input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return response.parsed_output, usage
