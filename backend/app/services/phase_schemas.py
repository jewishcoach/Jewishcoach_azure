"""
Pydantic models for structured output from the Supervisor.

NOTE: Stage definitions, names, and requirements are now managed exclusively 
in supervisor.py to maintain a single source of truth based on the PDF methodology.
"""

from pydantic import BaseModel
from typing import Literal

class InventoryCheck(BaseModel):
    """Component checklist for current phase"""
    component_1_found: bool
    component_2_found: bool = True  # Not all phases have 2 components
    details: str = ""  # What was found

class PhaseEvaluation(BaseModel):
    """Supervisor's evaluation of phase progress"""
    inventory_check: InventoryCheck
    decision: Literal["advance", "stay"]
    missing_components: str
    next_phase: str
    instructions_for_coach: str

