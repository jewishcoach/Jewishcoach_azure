"""
BSD V2 - Structured Output Schema for Coach Response

Uses Pydantic + Azure Structured Outputs (json_schema) to guarantee valid JSON.
Replaces fragile JSON Mode - the API physically cannot return invalid JSON.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field


class InternalStateSchema(BaseModel):
    """Internal state the coach must return each turn."""

    current_step: str = Field(
        description="השלב הנוכחי בתהליך לפי מתודת BSD, למשל S0, S1, S2 וכו'"
    )
    saturation_score: float = Field(
        description="ציון בין 0.0 ל-1.0 המייצג את מידת השהייה של המשתמש בשלב"
    )
    reflection: str = Field(
        description="חשיבה פנימית קצרה של המאמן לפני שהוא עונה"
    )
    collected_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="נתונים שנאספו בשלב הנוכחי (למשל topic ב-S1). יש לכלול רק נתונים רלוונטיים לשלב.",
    )


class CoachResponseSchema(BaseModel):
    """The complete response the model must return."""

    coach_message: str = Field(
        description="התגובה האמפתית למשתמש (Clean Language). ללא מונחים טכניים."
    )
    internal_state: InternalStateSchema = Field(
        description="מצב פנימי: current_step, saturation_score, reflection, collected_data"
    )
