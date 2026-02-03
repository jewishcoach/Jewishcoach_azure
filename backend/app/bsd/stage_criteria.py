from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
from .stage_defs import StageId

"""
Stage Completion Criteria for BSD methodology.

Defines what constitutes "completion" for each stage:
- Minimum messages required
- Required insights count
- Key indicators to look for
- Completion criteria (qualitative)

These are used by the Reasoner to evaluate readiness for stage transition.
"""


@dataclass(frozen=True)
class StageCriteria:
    """Completion criteria for a single stage"""
    stage_id: StageId
    min_messages: int  # Minimum number of user messages in this stage
    required_insights: int  # Number of key insights needed
    key_indicators: List[str]  # What to look for (Hebrew)
    completion_criteria: List[str]  # What must be achieved (Hebrew)


# Stage completion criteria (from old system + booklet)
STAGE_CRITERIA: Dict[StageId, StageCriteria] = {
    StageId.S0: StageCriteria(
        stage_id=StageId.S0,
        min_messages=1,
        required_insights=1,
        key_indicators=[
            "קבלת רשות מפורשת להתחיל"
        ],
        completion_criteria=[
            "המשתמש נתן הסכמה מפורשת (כן/בטח/אשמח)",
            "נוצר קשר ראשוני עם המאמן"
        ]
    ),
    
    StageId.S1: StageCriteria(
        stage_id=StageId.S1,
        min_messages=2,
        required_insights=1,
        key_indicators=[
            "זיהוי נושא/תחום לאימון",
            "הבנת התמודדות אותנטית"
        ],
        completion_criteria=[
            "המשתמש ביטא בבירור נושא לעבודה",
            "הנושא ספציפי מספיק (לא 'לא יודע')"
        ]
    ),
    
    StageId.S2: StageCriteria(
        stage_id=StageId.S2,
        min_messages=3,
        required_insights=1,
        key_indicators=[
            "תיאור אירוע ספציפי",
            "זיהוי מתי/עם מי/מה קרה",
            "רגש חזק באירוע"
        ],
        completion_criteria=[
            "המשתמש תיאר אירוע ספציפי (לא מצב כללי)",
            "האירוע כולל זמן, מקום, אנשים",
            "יש רגש משמעותי באירוע"
        ]
    ),
    
    StageId.S3: StageCriteria(
        stage_id=StageId.S3,
        min_messages=3,
        required_insights=4,  # At least 4 emotions
        key_indicators=[
            "זיהוי רגשות מגוונים",
            "עומק רגשי",
            "חיבור לרגש"
        ],
        completion_criteria=[
            "המשתמש זיהה לפחות 4 רגשות שונים",
            "הרגשות ספציפיים (לא כלליים)",
            "יש חיבור אמיתי לרגשות"
        ]
    ),
    
    StageId.S4: StageCriteria(
        stage_id=StageId.S4,
        min_messages=2,
        required_insights=1,
        key_indicators=[
            "זיהוי מחשבה מילולית",
            "משפט פנימי ברור"
        ],
        completion_criteria=[
            "המשתמש זיהה מחשבה ספציפית (משפט)",
            "המחשבה מילולית (לא רגש או פעולה)"
        ]
    ),
    
    StageId.S5: StageCriteria(
        stage_id=StageId.S5,
        min_messages=3,
        required_insights=2,  # Action actual + desired
        key_indicators=[
            "זיהוי מעשה בפועל",
            "זיהוי מעשה רצוי",
            "הבנת הפער בין המצוי לרצוי"
        ],
        completion_criteria=[
            "המשתמש תיאר מה עשה בפועל",
            "המשתמש תיאר מה רצה לעשות",
            "יש הבנה של הפער בין השניים"
        ]
    ),
    
    StageId.S2_READY: StageCriteria(
        stage_id=StageId.S2_READY,
        min_messages=3,
        required_insights=3,  # 3 questions answered
        key_indicators=[
            "חשיבות השינוי (1-10)",
            "אמונה באפשרות השינוי",
            "אמונה ביכולת אישית לשינוי"
        ],
        completion_criteria=[
            "המשתמש דירג חשיבות (רצוי 7+)",
            "המשתמש מאמין ששינוי אפשרי",
            "המשתמש מאמין שהוא מסוגל (אם לא → STOP)"
        ]
    ),
    
    StageId.S6: StageCriteria(
        stage_id=StageId.S6,
        min_messages=3,
        required_insights=2,  # Name + score
        key_indicators=[
            "זיהוי המצב הנוכחי",
            "הגדרת המצב הרצוי",
            "הבנת עומק הפער",
            "מתן שם לפער"
        ],
        completion_criteria=[
            "המשתמש נתן שם לפער",
            "המשתמש דירג את הפער (1-10)",
            "הובע רגש אמיתי לגבי הפער"
        ]
    ),
    
    StageId.S7: StageCriteria(
        stage_id=StageId.S7,
        min_messages=4,
        required_insights=2,  # Pattern + Paradigm
        key_indicators=[
            "זיהוי דפוס התנהגותי חוזר",
            "זיהוי דפוס מחשבתי",
            "הבנת חזרתיות הדפוס",
            "זיהוי פרדיגמה (מחשבת מעשה)"
        ],
        completion_criteria=[
            "המשתמש זיהה דפוס חוזר ספציפי",
            "הובנה השפעת הדפוס על החיים",
            "זוהתה פרדיגמה/אמונה שמניעה את הדפוס"
        ]
    ),
    
    StageId.S8: StageCriteria(
        stage_id=StageId.S8,
        min_messages=4,
        required_insights=2,  # Profit + Loss
        key_indicators=[
            "זיהוי תפיסת המציאות הנוכחית (עמדה)",
            "הבנת מקור העמדה",
            "חקירת תקפות העמדה",
            "ניתוח רווח והפסד"
        ],
        completion_criteria=[
            "זוהתה עמדה/תפיסה בסיסית",
            "המשתמש זיהה מה הוא מרוויח מהעמדה",
            "המשתמש זיהה מה זה עולה לו (הפסד)",
            "הופגנה פתיחות לבחינה מחדש"
        ]
    ),
    
    StageId.S9: StageCriteria(
        stage_id=StageId.S9,
        min_messages=4,
        required_insights=2,  # Source + Nature
        key_indicators=[
            "גילוי הנפש האלוקית האישית (מקור)",
            "זיהוי נטיות הגוף והכישורים (טבע)",
            "הבנת האיזון ביניהם",
            "יצירת חיבור למקור הפנימי"
        ],
        completion_criteria=[
            "זוהו כוחות המקור (ערכים, אמונות, מניעים)",
            "זוהו כוחות הטבע (כישורים, יכולות, חוכמות)",
            "נוצר 'כרטיס מהות-זהות' (כמ\"ז) אישי"
        ]
    ),
    
    StageId.S11: StageCriteria(
        stage_id=StageId.S11,
        min_messages=5,
        required_insights=3,  # New Stance + Paradigm + Pattern
        key_indicators=[
            "הפיכת כוח הבחירה לפעיל",
            "זיהוי אפשרויות בחירה",
            "יצירת מנגנון קבלת החלטות",
            "הפנמת כוח האחריות"
        ],
        completion_criteria=[
            "המשתמש בחר עמדה חדשה",
            "המשתמש בחר פרדיגמה חדשה",
            "המשתמש בחר דפוס חדש",
            "נוצרה 'קומה חדשה' ברורה",
            "הופגנה אחריות אישית לבחירות"
        ]
    ),
    
    StageId.S12: StageCriteria(
        stage_id=StageId.S12,
        min_messages=5,
        required_insights=3,  # Mission + Destiny + Heart's desire
        key_indicators=[
            "עיצוב חזון אישי ברור",
            "הגדרת שליחות אישית",
            "חיבור לחפץ הלב",
            "יצירת מוטיבציה להמשך"
        ],
        completion_criteria=[
            "נוצר חזון אישי ברור ומעורר השראה",
            "הוגדרה שליחות אישית",
            "יש חיבור רגשי לחזון",
            "הופגנה התחייבות רצינית להגשמת החזון"
        ]
    ),
    
    StageId.S10: StageCriteria(
        stage_id=StageId.S10,
        min_messages=3,
        required_insights=1,  # Complete formula
        key_indicators=[
            "למידה לבקש אימון ממוקד",
            "הגדרת יעדי השינוי",
            "יצירת תכנית יישום"
        ],
        completion_criteria=[
            "המשתמש ניסח בקשת אימון מלאה",
            "הבקשה כוללת: קושי + מקור/טבע + תוצאה מדידה",
            "הוגדרו יעדים ברורים ליישום"
        ]
    ),
}


def get_criteria(stage: StageId) -> StageCriteria | None:
    """Get completion criteria for a stage"""
    return STAGE_CRITERIA.get(stage)


def get_min_messages(stage: StageId) -> int:
    """Get minimum messages required for a stage"""
    criteria = get_criteria(stage)
    return criteria.min_messages if criteria else 2


def get_required_insights(stage: StageId) -> int:
    """Get required insights count for a stage"""
    criteria = get_criteria(stage)
    return criteria.required_insights if criteria else 1


# Public API
__all__ = [
    "StageCriteria",
    "STAGE_CRITERIA",
    "get_criteria",
    "get_min_messages",
    "get_required_insights",
]

