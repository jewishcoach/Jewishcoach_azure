from __future__ import annotations

from typing import Literal, Optional

from .stage_defs import StageId, is_valid_stage

"""
Hard-coded injection scripts (per the report + PDFs).

These texts should be treated as methodology-ground-truth. The Talker may add
a short empathic bridge, but must not rewrite the professional wording.

Enterprise-grade: Type-safe language parameter + validation + no silent failures.
"""

Language = Literal["he", "en"]
Gender = Literal["male", "female"]

# Public API
__all__ = ["get_script", "ScriptNotFoundError", "Language", "adapt_to_gender"]


def adapt_to_gender(text: str, gender: Optional[str], language: str = "he") -> str:
    """
    Adapt text to match user's gender by replacing gender-neutral forms.
    
    Args:
        text: The text to adapt
        gender: User's gender ("male", "female", or None)
        language: Language of the text ("he" or "en")
    
    Returns:
        Text adapted to the specified gender
    
    Examples:
        >>> adapt_to_gender("בוא/י נתחיל", "male", "he")
        'בוא נתחיל'
        >>> adapt_to_gender("בוא/י נתחיל", "female", "he")
        'בואי נתחיל'
    """
    if not gender or language != "he":
        return text
    
    if gender == "male":
        # Male forms in Hebrew
        replacements = {
            "בוא/י": "בוא",
            "את/ה": "אתה",
            "מבקש/ת": "מבקש",
            "תן/י": "תן",
            "כתוב/י": "ספר",
            "ספר/י": "ספר",
            "ציין/י": "ציין",
            "רוצה": "רוצה",
            "היית": "היית",
            "השלם/י": "השלם",
            "מזהה": "מזהה",
            "תרצה/י": "תרצה",
            "תהיה/י": "תהיה",
            "ספציפי/ת": "ספציפי",
            "היית רוצה": "היית רוצה",
        }
    elif gender == "female":
        # Female forms in Hebrew
        replacements = {
            "בוא/י": "בואי",
            "את/ה": "את",
            "מבקש/ת": "מבקשת",
            "תן/י": "תני",
            "כתוב/י": "ספרי",
            "ספר/י": "ספרי",
            "ציין/י": "ציני",
            "רוצה": "רוצה",
            "היית": "היית",
            "השלם/י": "השלימי",
            "מזהה": "מזהה",
            "תרצה/י": "תרצי",
            "תהיה/י": "תהיי",
            "ספציפי/ת": "ספציפית",
            "היית רוצה": "היית רוצה",
        }
    else:
        return text
    
    # Apply replacements
    result = text
    for neutral, gendered in replacements.items():
        result = result.replace(neutral, gendered)
    
    return result


SCRIPTS_HE: dict[str, str] = {
    "S0": (
        "שלום רב! שמח שהצטרפת.\n\n"
        "אני המאמן הווירטואלי שלך. הוכשרתי לפעול על פי **שיטת האימון היהודי (BSD)** שפיתח בני גל – "
        "גישה המחברת את תורת הנפש היהודית עם כלים מעשיים ומקצועיים לשינוי וצמיחה.\n\n"
        "אני כאן כדי לעזור לך לזהות את **הרצון** האמיתי שלך, להתגבר על חסמים ודפוסים, "
        "ולצאת לדרך של עשייה משמחת ומדויקת יותר. "
        "הדרך שבה נצעד יחד נקראת **'תהליך השיבה'** – שיבה אל עצמך ואל המקור שלך.\n\n"
        "חשוב לי לומר: התשובות נמצאות אצלך. התפקיד שלי הוא לשאול שאלות שיאפשרו להן להתגלות, "
        "בקצב שלך ובכיוון שתבחר.\n\n"
        "**האם יש לי רשות להתחיל איתך את תהליך האימון?**"
    ),
    "S1": (
        "אז בואו נתחיל.\n\n"
        "על מה היית רוצה שנעבוד היום?"
    ),
    "S2": (
        "בשביל לעבוד על זה באמת, אני צריך שנביא רגע אמיתי מהחיים.\n\n"
        "ספר/י לי על פעם אחת לאחרונה שזה קרה – "
        "מתי זה היה? עם מי? מה בדיוק קרה?\n\n"
        "לדוגמה: \"אתמול בערב ביקשתי מהילד לעשות שיעורים, הוא סירב, צעקתי עליו, והוא הלך לחדר.\""
    ),
    "S2_READY": (
        "תודה שתיארת את המצב.\n\n"
        "לפני שנמשיך, אני רוצה לבדוק משהו – "
        "האם יש לנו את האנרגיה להמשיך במסע הזה.\n\n"
        "3 שאלות קצרות:\n\n"
        "**1. עד כמה חשוב לך שהמצב הזה ישתנה?**\n"
        "(מ-1 עד 10)\n\n"
        "**2. האם את/ה מאמין/ה ששינוי כזה בכלל אפשרי?**\n\n"
        "**3. והכי חשוב – האם את/ה מאמין/ה שאת/ה מסוגל/ת לעשות את השינוי הזה?**"
    ),
    "S3": (
        "אוקיי, עכשיו בוא/י נסתכל על מה שהרגשת באותו רגע.\n\n"
        "אילו רגשות עלו בך? תחושות פנימיות – "
        "כעס, תסכול, עצב, בושה, פחד, אשמה...\n\n"
        "נסה/י לזהות לפחות 3-4 רגשות שהיו שם.\n\n"
        "(רק שים/י לב – אני מחפש רגשות, לא מחשבות כמו \"אני כישלון\" או פעולות כמו \"צעקתי\". "
        "רק תחושות.)"
    ),
    "S4": (
        "טוב. מאחורי הרגשות האלה יש בדרך כלל גם משפט שעובר בראש.\n\n"
        "מה המחשבה שהייתה לך באותו רגע? איזה משפט אמרת לעצמך?\n\n"
        "לדוגמה: \"אני אב רע\", \"הוא לא מכבד אותי\", \"אני לא מספיק טוב\"...\n\n"
        "(רק שתדע/י – אני מחפש מחשבה, לא פעולה כמו \"צעקתי\" ולא רגש כמו \"כעס\". "
        "משפט שחשבת בראש.)"
    ),
    "S5": (
        "עכשיו בוא/י נסתכל על מה שקרה בפועל.\n\n"
        "מה עשית באותו רגע? איך הגבת?"
    ),
    "S6": (
        "אוקיי, אז יש לנו תמונה מלאה – איך זה היה, ואיך היית רוצה שזה יהיה.\n\n"
        "המרחק ביניהם, הפער הזה – איך היית קורא לו? תן/י לו שם.\n"
        "ואם היית צריך/ה לציין, איזה ציון היית נותן/ת לעוצמה של הפער הזה, בין 1 ל-10?"
    ),
    "S7": (
        "שאלה – האירוע הזה, זה משהו חד-פעמי או שזה קורה הרבה?\n\n"
        "אם זה חוזר על עצמו, מה הדפוס? מה התבנית החוזרת?\n"
        "ויש איזו אמונה שיושבת לך בראש – \"ככה זה\", \"ככה אני\" – שגורמת לזה לחזור?"
    ),
    "S8": (
        "אוקיי, יש כאן דפוס ופרדיגמה שזיהינו. עכשיו בוא/י נעמיק יותר.\n\n"
        "יש כאן משהו עמוק יותר – **עמדה**, תפיסת עולם שורשית.\n\n"
        "בוא/י נבחן את זה דרך שתי שאלות:\n\n"
        "**1. מה את/ה מרוויח/ה מהעמדה הזו?**\n"
        "(מה הרווחים, הנוחות, ההגנות שהיא נותנת לך?)\n\n"
        "**2. ומה ההפסד? מה זה עולה לך?**\n"
        "(מה אתה מפספס? מה המחיר שאתה משלם?)"
    ),
    "S9": (
        "יפה. עכשיו בוא/י נאסוף את הכוחות שיש לך בשביל המסע הזה.\n\n"
        "מה הכוחות העמוקים שלך – הערכים, האמונות, מה שמניע אותך מבפנים? (זה **המקור** שלך)\n\n"
        "ומה הכישורים והיכולות שיש לך – החוכמות, הכישרונות, הכלים המעשיים? (זה **הטבע** שלך)\n\n"
        "יחד, זה הכמ\"ז שלך – כרטיס המהות-זהות שלך."
    ),
    "S11": (
        "עכשיו כשיש לך את התמונה המלאה – הדפוס הישן, העמדה, והכוחות שלך –\n"
        "הגיע הזמן **לבחור מחדש**.\n\n"
        "מתוך המקור והטבע שזיהית, מה הבחירה החדשה שלך?\n\n"
        "**1. איזו עמדה חדשה את/ה בוחר/ת?**\n"
        "(תפיסת עולם חדשה שתשמש אותך יותר טוב)\n\n"
        "**2. איזו פרדיגמה חדשה?**\n"
        "(מחשבת מעשה חדשה שתוביל אותך)\n\n"
        "**3. ואיזה דפוס חדש את/ה רוצה ליצור?**\n"
        "(התנהגות חדשה שתחליף את הישנה)\n\n"
        "זו ה**קומה החדשה** שלך."
    ),
    "S12": (
        "יפה מאוד. עכשיו בוא/י נרחיב את המבט.\n\n"
        "זה לא רק על אירוע אחד או דפוס אחד – זה על **חייך כולם**.\n\n"
        "אם תסתכל/י קדימה, על החיים שאת/ה רוצה לעצב מתוך הקומה החדשה הזו –\n"
        "**מה החזון שלך?**\n\n"
        "- מה השליחות האישית שלך?\n"
        "- לאן אתה רוצה להגיע?\n"
        "- מה חפץ הלב שלך?\n\n"
        "ספר/י לי על התמונה הגדולה."
    ),
    "S10": (
        "אנחנו כמעט שם. עכשיו בוא/י נסכם את כל מה שעלה במשפט אחד ברור.\n\n"
        "השלם/י את המשפט הזה בצורה שמדברת אליך:\n\n"
        "**\"אני מבקש/ת להתאמן על הקושי להתמודד עם ____________________________**\n"
        "**(הדפוס/הפרדיגמה/העמדה הישנים),**\n\n"
        "**כך שאפעל מתוך המקור והטבע שלי ומתוך הקומה החדשה שבחרתי,**\n\n"
        "**כדי שהתוצאה שאשיג תהיה ____________________________ .\"**\n"
        "(תוצאה מדידה וברורה)"
    ),
}


SCRIPTS_EN: dict[str, str] = {
    "S0": (
        "Hello! I'm glad you joined.\n\n"
        "I am your virtual coach. I've been trained according to the **BSD (Jewish Coaching) Method** developed by Beni Gal – "
        "an approach that connects the Jewish psychology with practical, professional tools for change and growth.\n\n"
        "I'm here to help you identify your true **Ratson** (Will), overcome barriers and patterns, "
        "and embark on a path of joyful and precise action. "
        "The journey we'll take together is called **'The Return Process'** (Teshuvah) – returning to yourself and to your Source.\n\n"
        "It's important for me to say: The answers are within you. My role is to ask questions that will allow them to emerge, "
        "at your pace and in the direction you choose.\n\n"
        "**Do I have your permission to begin the coaching process with you?**"
    ),
    "S1": (
        "So let's begin.\n\n"
        "What would you like to work on today? "
        "What area of your life is calling for your attention right now?"
    ),
    "S2": (
        "To work on this in a real way, I need us to bring an actual moment from life.\n\n"
        "Tell me about one time recently when this happened – "
        "when was it? who was involved? what exactly happened?\n\n"
        "For example: \"Yesterday evening I asked my child to do homework, he refused, I yelled at him, and he went to his room.\""
    ),
    "S2_READY": (
        "Thank you for describing the situation in detail.\n\n"
        "Now, before we continue, I want to check our **'engine'** – "
        "whether we have enough fuel to continue this journey.\n\n"
        "3 short questions:\n\n"
        "**1. How important is it to you that this situation changes?**\n"
        "(From 1 to 10)\n\n"
        "**2. Do you believe that such a change is even possible in reality?**\n\n"
        "**3. And most importantly – do you believe that **you** are capable of making this change?**"
    ),
    "S3": (
        "Okay, now let's look at what you felt in that moment.\n\n"
        "What emotions came up for you? I'm looking for inner feelings – "
        "anger, frustration, sadness, shame, fear, guilt...\n\n"
        "If possible, try to identify at least 3-4 emotions that were there.\n\n"
        "(Just note – I'm looking for emotions, not thoughts like \"I'm a failure\" or actions like \"I yelled\". "
        "Just feelings.)"
    ),
    "S4": (
        "Good. Behind those emotions, there's usually also a sentence running through your head.\n\n"
        "What was the thought you had in that moment? What sentence did you tell yourself?\n\n"
        "For example: \"I'm a bad parent\", \"He doesn't respect me\", \"I'm not good enough\"...\n\n"
        "(Just so you know – I'm looking for a thought, not an action like \"I yelled\" or an emotion like \"anger\". "
        "A sentence you thought in your head.)"
    ),
    "S5": (
        "Now let's look at what actually happened.\n\n"
        "What did you do in that moment? How did you respond?"
    ),
    "S6": (
        "Okay, so we have a full picture – how it was, and how you'd like it to be.\n\n"
        "The distance between them, this gap – what would you call it? Give it a name.\n"
        "And if you had to rate the intensity of this gap, what rating would you give it, from 1 to 10?"
    ),
    "S7": (
        "Question – this event, is it a one-time thing or does it happen a lot?\n\n"
        "If it repeats itself, what's the pattern? What recurring template do you recognize?\n"
        "And is there a basic belief, something you quietly believe – \"that's how it is\", \"that's who I am\" – that drives this pattern?"
    ),
    "S8": (
        "Okay, we've identified a pattern and paradigm here. Now let's go deeper.\n\n"
        "There's something even deeper here – a **Stance**, a root worldview.\n\n"
        "Let's examine it through two questions:\n\n"
        "**1. What do you GAIN from this stance?**\n"
        "(What are the benefits, comforts, protections it gives you?)\n\n"
        "**2. And what's the LOSS? What does it cost you?**\n"
        "(What are you missing? What price are you paying?)"
    ),
    "S9": (
        "Good. Now let's gather the forces you have for this journey.\n\n"
        "What are your deep forces – the values, beliefs, what drives you from within? (This is your **Source**)\n\n"
        "And what skills and abilities do you have – the wisdom, talents, practical tools? (This is your **Nature**)\n\n"
        "Together, this is your KaMaZ – your Core Essence Card."
    ),
    "S11": (
        "Now that you have the full picture – the old pattern, the stance, and your forces –\n"
        "it's time to **choose anew**.\n\n"
        "From the Source and Nature you identified, what's your new choice?\n\n"
        "**1. What new stance do you choose?**\n"
        "(A new worldview that will serve you better)\n\n"
        "**2. What new paradigm?**\n"
        "(A new action-thought that will guide you)\n\n"
        "**3. And what new pattern do you want to create?**\n"
        "(A new behavior to replace the old one)\n\n"
        "This is your **New Floor**."
    ),
    "S12": (
        "Very good. Now let's expand the view.\n\n"
        "This isn't just about one event or one pattern – it's about **your whole life**.\n\n"
        "If you look forward, at the life you want to create from this new floor –\n"
        "**what's your vision?**\n\n"
        "- What's your personal mission?\n"
        "- Where do you want to go?\n"
        "- What's your heart's desire?\n\n"
        "Tell me about the big picture."
    ),
    "S10": (
        "We're almost there. Now let's summarize everything that came up in one clear sentence.\n\n"
        "Complete this sentence in a way that speaks to you:\n\n"
        "**\"I ask to train on the difficulty of dealing with ____________________________**\n"
        "**(the old pattern/paradigm/stance),**\n\n"
        "**so that I act from my Source and Nature and from the new floor I chose,**\n\n"
        "**so that the result I achieve will be ____________________________ .\"**\n"
        "(A measurable, clear result)"
    ),
}


class ScriptNotFoundError(Exception):
    """Raised when a script is not found for a given stage/language"""
    pass


LOOP_PROMPTS_HE: dict[StageId, str] = {
    StageId.S0: "האם יש לי רשות להתחיל?",
    StageId.S1: "על מה את/ה רוצה להתאמן עכשיו?",
    StageId.S2: "תן/י דוגמה לאירוע ספציפי: **מה קרה** + **עם מי** + **מתי**.",
    StageId.S2_READY: "ענה/י בבקשה על 3 השאלות: חשיבות (1-10), האם שינוי אפשרי, והאם **את/ה** מסוגל/ת.",
    StageId.S3: "חסר עוד {missing} רגש{suffix}. איזה עוד **רגש** היה שם? (לדוגמה: כעס, תסכול, בושה, פחד)",
    StageId.S4: "מה הייתה **המחשבה** שעברה בך? (משפט אחד, לדוגמה: \"אני אב רע\")",
    StageId.S5: "מה **עשית בפועל**? (פעולה קונקרטית, לדוגמה: \"צעקתי עליו\")",
    StageId.S6: "תן/י שם לפער וציין/י ציון בין 1 ל-10.",
    StageId.S7: "האם את/ה מזהה כאן דפוס? מהי האמונה שמפעילה אותו?",
    StageId.S8: "מי היית רוצה להיות שם?",
    StageId.S9: "ספר/י כוחות מקור וכוחות טבע.",
    StageId.S10: "השלם/י את הבקשה כך שתשקף את מה שבחרת.",
}

LOOP_PROMPTS_EN: dict[StageId, str] = {
    StageId.S0: "Do I have your permission to begin?",
    StageId.S1: "What would you like to coach on now?",
    StageId.S2: "Please give one specific recent event.",
    StageId.S2_READY: "Please answer the 3 questions: importance (1-10), is change possible, and are **you** capable.",
    StageId.S3: "Need {missing} more emotion{suffix}. What other emotion was there?",
    StageId.S4: "What was the verbal thought that passed through you?",
    StageId.S5: "What did you actually do in that situation?",
    StageId.S6: "Give the gap a name and rate it 1-10.",
    StageId.S7: "Do you identify a pattern? What belief activates it?",
    StageId.S8: "Who would you like to be there?",
    StageId.S9: "Write down Source forces and Nature forces.",
    StageId.S10: "Complete the commitment formula.",
}


def get_script(
    stage_id: str | StageId, 
    *, 
    language: Language | str = "he",
    gender: Optional[str] = None
) -> str:
    """
    Get the hard-coded script for a stage, adapted to user's gender.
    
    Args:
        stage_id: Stage identifier (accepts both str and StageId enum)
        language: "he" or "en"
        gender: User's gender ("male", "female", or None) - used to adapt Hebrew text
    
    Returns:
        The script text for the stage, adapted to the user's gender
    
    Raises:
        ScriptNotFoundError: If stage_id is invalid or script not found
        ValueError: If language is invalid
    
    Examples:
        >>> get_script("S0", language="he", gender="male")
        'לפני שמתחילים, חשוב לי לדייק את המסגרת...'
        
        >>> get_script(StageId.S1, language="he", gender="female")
        "בואי נתחיל מהמקום שבו הרצון מבקש להופיע..."
    """
    # Validate language
    if language not in ("he", "en"):
        raise ValueError(f"Invalid language: {language}. Must be 'he' or 'en'.")
    
    # Handle both string and StageId enum
    stage_key = stage_id.value if isinstance(stage_id, StageId) else stage_id
    
    # Validate stage
    if not is_valid_stage(stage_key):
        raise ScriptNotFoundError(
            f"Invalid stage: {stage_key}. "
            f"Valid stages: S0-S10"
        )
    
    # Get script
    scripts = SCRIPTS_HE if language == "he" else SCRIPTS_EN
    script = scripts.get(stage_key)
    
    if not script:
        raise ScriptNotFoundError(
            f"No script found for stage {stage_key} in language '{language}'. "
            f"This is a configuration error - all stages must have scripts."
        )
    
    # Adapt to gender if Hebrew
    if language == "he" and gender:
        script = adapt_to_gender(script, gender, language)
    
    return script


def get_loop_prompt(
    stage_id: str | StageId,
    *,
    language: Language | str = "he",
    missing: int = 1,
    gender: Optional[str] = None
) -> str:
    """
    Retrieves a short, focused loop prompt for when the user needs to provide more info.
    
    Loop prompts are shorter and more targeted than the full stage script,
    avoiding the "broken record" feeling of repeating the entire script on each loop.
    
    Args:
        stage_id: The ID of the stage (e.g., "S0", StageId.S3).
        language: The desired language ("he" or "en"). Defaults to "he".
        missing: For S3, the number of missing emotions (used for formatting).
        gender: User's gender ("male", "female", or None) - used to adapt Hebrew text
    
    Returns:
        The loop prompt as a string, adapted to the user's gender.
    
    Raises:
        ValueError: If the provided language is not 'he' or 'en'.
        ScriptNotFoundError: If the stage_id is invalid or no loop prompt is found.
    """
    if language not in ("he", "en"):
        raise ValueError(f"Invalid language: {language}. Must be 'he' or 'en'.")
    
    try:
        stage_key = StageId(stage_id)
    except ValueError:
        raise ScriptNotFoundError(f"Invalid stage: {stage_id}. Valid stages: S0-S10")
    
    prompts = LOOP_PROMPTS_HE if language == "he" else LOOP_PROMPTS_EN
    prompt = prompts.get(stage_key)
    
    if prompt is None:
        raise ScriptNotFoundError(
            f"No loop prompt found for stage '{stage_key.value}' in '{language}'."
        )
    
    # Format S3 prompt with missing count
    if stage_key == StageId.S3:
        suffix = "ות" if missing > 1 else "" if language == "he" else "s" if missing > 1 else ""
        prompt = prompt.format(missing=missing, suffix=suffix)
    
    # Adapt to gender if Hebrew
    if language == "he" and gender:
        prompt = adapt_to_gender(prompt, gender, language)
    
    return prompt


