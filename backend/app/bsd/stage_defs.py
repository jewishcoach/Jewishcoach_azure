from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

"""
Stage definitions (S0 through S13) for BSD methodology.

Enterprise-grade: Type-safe StageId enum + validation + metadata.

Full methodology progression (11 stages from booklet):
1. S0 - Coaching Contract (חוזה האימון)
2. S1 - Unloading/Topic (המצוי)
3. S2 - Isolate Event (בידוד האירוע)
4. S3-S5 - Three Screens (שלושת המסכים): Emotion, Thought, Action
5. S2_READY - Readiness Check (המנוע המשולש)
6. S6 - Gap Analysis (ניתוח הפער)
7. S7 - Pattern & Paradigm (דפוס ופרדיגמה)
8. S8 - Stance (העמדה - רווח והפסד)
9. S9 - KaMaZ (כמ"ז - מקור וטבע)
10. S11 - Renewal & Choice (התחדשות ובחירה חדשה)
11. S12 - Vision (חזון - חפץ הלב)
12. S10 - Commitment Formula (נוסחת המחויבות) [Final stage]
"""


class StageId(str, Enum):
    """Type-safe stage identifiers"""
    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S2_READY = "S2_READY"  # Readiness Check (Triple Engine)
    S3 = "S3"
    S4 = "S4"
    S5 = "S5"
    S6 = "S6"
    S7 = "S7"
    S8 = "S8"  # Changed: Now "Stance" instead of "Being"
    S9 = "S9"
    S11 = "S11"  # NEW: Renewal & Choice
    S12 = "S12"  # NEW: Vision
    S10 = "S10"  # Final: Commitment (remains last)


@dataclass(frozen=True)
class StageDef:
    """Metadata for each stage"""
    id: StageId
    name_he: str
    name_en: str
    prompt_key: str


# Ordered progression of stages (immutable)
# Updated to match the full BSD methodology from booklet (11 stages)
STAGE_ORDER: List[StageId] = [
    StageId.S0,        # 1. Coaching Contract
    StageId.S1,        # 2. Unloading/Topic
    StageId.S2,        # 3. Isolate Event
    StageId.S3,        # 4. Screen 1: Emotion
    StageId.S4,        # 5. Screen 2: Thought
    StageId.S5,        # 6. Screen 3: Action
    StageId.S2_READY,  # 7. Readiness Check (The Engine)
    StageId.S6,        # 8. Gap Analysis
    StageId.S7,        # 9. Pattern & Paradigm
    StageId.S8,        # 10. Stance (Profit & Loss)
    StageId.S9,        # 11. KaMaZ (Source & Nature)
    StageId.S11,       # 12. Renewal & Choice (New Floor)
    StageId.S12,       # 13. Vision (Heart's Desire)
    StageId.S10        # 14. Commitment Formula (FINAL)
]


# Stage definitions with Hebrew/English names
# Updated to reflect full BSD methodology from booklet
STAGES: Dict[StageId, StageDef] = {
    StageId.S0: StageDef(id=StageId.S0, name_he="חוזה האימון", name_en="Coaching Contract", prompt_key="S0"),
    StageId.S1: StageDef(id=StageId.S1, name_he="המצוי", name_en="Unloading", prompt_key="S1"),
    StageId.S2: StageDef(id=StageId.S2, name_he="בידוד האירוע", name_en="Isolate Event", prompt_key="S2"),
    StageId.S2_READY: StageDef(id=StageId.S2_READY, name_he="בדיקת נכונות", name_en="Readiness Check", prompt_key="S2_READY"),
    StageId.S3: StageDef(id=StageId.S3, name_he="מסך 1: רגש", name_en="Screen 1: Emotion", prompt_key="S3"),
    StageId.S4: StageDef(id=StageId.S4, name_he="מסך 2: מחשבה", name_en="Screen 2: Thought", prompt_key="S4"),
    StageId.S5: StageDef(id=StageId.S5, name_he="מסך 3: מעשה", name_en="Screen 3: Action", prompt_key="S5"),
    StageId.S6: StageDef(id=StageId.S6, name_he="ניתוח הפער", name_en="Gap Analysis", prompt_key="S6"),
    StageId.S7: StageDef(id=StageId.S7, name_he="דפוס ופרדיגמה", name_en="Pattern & Paradigm", prompt_key="S7"),
    StageId.S8: StageDef(id=StageId.S8, name_he="העמדה", name_en="Stance", prompt_key="S8"),  # CHANGED from "בירור הרצון"
    StageId.S9: StageDef(id=StageId.S9, name_he="בניית כמ\"ז", name_en="Build KaMaZ", prompt_key="S9"),
    StageId.S11: StageDef(id=StageId.S11, name_he="התחדשות ובחירה", name_en="Renewal & Choice", prompt_key="S11"),  # NEW
    StageId.S12: StageDef(id=StageId.S12, name_he="חזון", name_en="Vision", prompt_key="S12"),  # NEW
    StageId.S10: StageDef(id=StageId.S10, name_he="נוסחת המחויבות", name_en="Commitment Formula", prompt_key="S10"),  # FINAL
}


def is_valid_stage(stage: str) -> bool:
    """Check if a stage string is valid"""
    try:
        StageId(stage)
        return True
    except (ValueError, KeyError):
        return False


def next_stage(stage: StageId | str) -> StageId | None:
    """
    Return the next stage in the progression.
    
    For example:
      next_stage("S0") -> StageId.S1
      next_stage("S10") -> None (final stage)
    """
    try:
        stg = StageId(stage) if not isinstance(stage, StageId) else stage
        idx = STAGE_ORDER.index(stg)
        if idx + 1 < len(STAGE_ORDER):
            return STAGE_ORDER[idx + 1]
        return None
    except (ValueError, KeyError):
        return None


# Backward compatibility: export stage IDs as strings
STAGES_LIST = [s.value for s in STAGE_ORDER]
