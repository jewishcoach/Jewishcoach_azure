"""
BSD Session Script - Preview
==============================
Shows the complete simulation script without actually running the LLM
"""

# Simulated user responses for each stage
SIMULATION_SCRIPT = {
    "S0": {
        "stage_name": "רשות (Consent)",
        "coach_script": "לפני שמתחילים, חשוב לי לדייק את המסגרת.\nבתהליך הזה אני לא מביא תשובות – אלא מחזיק דרך.\nהאם יש לי רשות להתחיל איתך את התהליך?",
        "user_response": "כן, אני מסכים",
        "gate_condition": "User must give explicit consent"
    },
    "S1": {
        "stage_name": "נושא (Topic)",
        "coach_script": "בוא/י נתחיל מהמקום שבו הרצון מבקש להופיע.\nעל מה את/ה מבקש/ת להתאמן עכשיו?",
        "user_response": "אני רוצה להתאמן על הורות - איך להניע את הילדים שלי לעזור בבית",
        "gate_condition": "User states a general topic/area"
    },
    "S2": {
        "stage_name": "אירוע (Event)",
        "coach_script": "כדי לעבוד בצורה מדויקת, נביא רגע אחד מהחיים.\nתן/י דוגמה לאירוע ספציפי שקרה לאחרונה, שבו התעורר בך רגש חזק והיו מעורבים בו אנשים נוספים.",
        "user_response": """אתמול בערב ביקשתי מהבן שלי בן ה-12 לאסוף את הכלים מהשולחן אחרי ארוחת ערב. 
הוא אמר "רגע אבא, אני באמצע משחק" ולא זז. אני חזרתי על הבקשה פעמיים נוספות, 
הוא המשיך להתעלם. בסוף צעקתי עליו "תקום עכשיו!" והוא קם בכעס, זרק את הכלים בכיור 
ונעלם לחדר. אשתי הסתכלה עלי במבט מאשים.""",
        "gate_condition": "Specific recent event with emotions and other people"
    },
    "S3": {
        "stage_name": "מסך הרגש (Emotion Screen)",
        "coach_script": "עכשיו נעשה סדר בחוויה, כדי לראות אותה בבהירות.\nנתחיל במסך הרגש:\nאילו רגשות התעוררו בך באותו רגע? כתוב/י לפחות ארבעה.",
        "user_response": "כעס, תסכול, אשמה, חוסר אונים",
        "gate_condition": "At least 4 distinct emotions"
    },
    "S4": {
        "stage_name": "מסך המחשבה (Thought Screen)",
        "coach_script": "מאחורי הרגש יש בדרך כלל משפט פנימי.\nמה הייתה המחשבה המילולית שעברה בך באותו רגע? משפט אחד.",
        "user_response": "חשבתי לעצמי: 'למה הוא תמיד עושה לי את זה? אני לא מבקש הרבה, רק מעט עזרה בבית!'",
        "gate_condition": "Specific thought (not emotion)"
    },
    "S5": {
        "stage_name": "מסך המעשה (Action Screen)",
        "coach_script": "עכשיו נישאר בעובדות בלבד.\nמה עשית בפועל באותה סיטואציה? בלי הסברים ובלי פרשנות.",
        "user_response": "צעקתי עליו בקול רם, אמרתי 'תקום עכשיו!', עמדתי מעליו עד שקם",
        "gate_condition": "Actions only, no interpretations"
    },
    "S6": {
        "stage_name": "פער (Gap)",
        "coach_script": "מתוך מה שתיארת, מתגלה פער.\nתן/י לפער הזה שם, וציין/י את עוצמתו במספר בין 1 ל-10.",
        "user_response": "הפער בין מי שאני למי שהייתי רוצה להיות - 8. אני קורא לזה 'פער בין דורש לממריץ'",
        "gate_condition": "Gap name and rating 1-10"
    },
    "S7": {
        "stage_name": "דפוס ופרדיגמה (Pattern & Paradigm)",
        "coach_script": "עכשיו נבדוק אם זה אירוע חד-פעמי או משהו שחוזר על עצמו.\nהאם את/ה מזהה כאן דפוס? ומהי האמונה או ה\"ככה זה\" שמפעילה אותו?",
        "user_response": """כן, אני מזהה דפוס חוזר: כל פעם שאני מבקש מהילדים משהו והם לא מגיבים מיד, 
אני עובר ישר למצב של דרישה וכפייה. האמונה שמפעילה את זה היא 'אם אני לא אהיה נחוש 
ותקיף, הם לא יעשו כלום ויפנקו אותי'.""",
        "gate_condition": "Recurring pattern + driving belief"
    },
    "S8": {
        "stage_name": "קומה חדשה (New Identity)",
        "coach_script": "לפני שנדבר על פעולה, נעצור בזהות.\nמי היית רוצה להיות שם? לא מה לעשות – מי להיות.",
        "user_response": """הייתי רוצה להיות אבא שממריץ ומעורר רצון פנימי, לא אבא שכופה. 
אבא שהילדים שלו רוצים לעזור כי הם מבינים את החשיבות, לא כי הם פוחדים.""",
        "gate_condition": "Identity/Being (not action)"
    },
    "S9": {
        "stage_name": "כמ\"ז (Source & Nature Forces)",
        "coach_script": "עכשיו נאסוף את הכוחות שפועלים בך.\nכתוב/י כוחות מקור (ערכים, אמונה) וכוחות טבע (כישרונות, שכל).",
        "user_response": """כוחות מקור: אמונה שלילדים יש ערך פנימי וחשיבה עצמאית (צלם אלוקים), 
ערך של חינוך לאחריות ולא רק ציות.
כוחות טבע: יכולת להסביר ולתקשר בבהירות, סבלנות כשאני רגוע, הבנה פסיכולוגית.""",
        "gate_condition": "Source forces (values) + Nature forces (talents)"
    },
    "S10": {
        "stage_name": "התחייבות (Commitment)",
        "coach_script": """נחתום את התהליך בניסוח בהיר אחד.
השלם/י את הבקשה כך שתשקף במדויק את מה שבחרת:

אני מבקש/ת להתאמן על הקושי להתמודד עם ____________________________ ,
כך שאפעל מתוך המקור שלי ומתוך הקומה החדשה שבחרתי,
כדי שהתוצאה שאשיג תהיה ____________________________ .""",
        "user_response": """אני מבקש להתאמן על הקושי להתמודד עם התנגדות של הילדים לעזרה בבית,
כך שאפעל מתוך המקור שלי - אמונה ביכולת שלהם - ומתוך הזהות החדשה - אבא ממריץ,
כדי שהתוצאה המדידה שאשיג תהיה שהילדים יתחילו לעזור מיוזמתם הם לפחות פעמיים בשבוע.""",
        "gate_condition": "Complete commitment statement"
    },
}


def print_simulation():
    print("=" * 100)
    print("BSD FULL SESSION SIMULATION SCRIPT")
    print("=" * 100)
    print("Scenario: אבא מנסה להניע את ילדיו לעזרה בבית")
    print("=" * 100)
    print()
    
    for stage_id in ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"]:
        stage_data = SIMULATION_SCRIPT.get(stage_id)
        if not stage_data:
            continue
        
        print(f"\n{'=' * 100}")
        print(f"שלב {stage_id}: {stage_data['stage_name']}")
        print(f"{'=' * 100}")
        print()
        print(f"📋 Gate Condition: {stage_data['gate_condition']}")
        print()
        print(f"🤖 COACH:")
        print(f"   {stage_data['coach_script']}")
        print()
        print(f"👤 USER:")
        for line in stage_data['user_response'].split('\n'):
            print(f"   {line}")
        print()
    
    print("=" * 100)
    print("🎉 SESSION COMPLETE - All 11 stages")
    print("=" * 100)
    print()
    print("📊 SUMMARY:")
    print()
    print("התוצאה:")
    print("- האבא זיהה דפוס של כפייה ודרישה")
    print("- הוא בחר בזהות חדשה: 'אבא ממריץ'")
    print("- הוא מתחייב לפעול מתוך אמונה ביכולת הילדים")
    print("- מטרה מדידה: ילדים עוזרים מיוזמתם פעמיים בשבוע")
    print()


if __name__ == "__main__":
    print_simulation()

