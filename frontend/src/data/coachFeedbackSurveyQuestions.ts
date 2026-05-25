export type SurveyChoiceOption = {
  value: string;
  label: string;
};

export type SurveyQuestion = {
  key: string;
  title: string;
  options: SurveyChoiceOption[];
  allowOther?: boolean;
};

export type SurveySection = {
  id: string;
  title: string;
  questions: SurveyQuestion[];
};

export const COACH_FEEDBACK_SURVEY_TITLE =
  'שאלון משוב מאמנים – תהליך השיבה באפליקציה';

export const COACH_FEEDBACK_SURVEY_INTRO =
  'ראשית תודה על הזמן שאתם מקדישים להתנסות במערכת שלנו! מטרת ההתנסות היא לבחון עד כמה האפליקציה מצליחה להעביר תהליך אימוני אותנטי, עמוק ואפקטיבי, תוך נאמנות למתודולוגיה של "תהליך השיבה". נודה לכם על כנות מקסימלית!';

export const COACH_FEEDBACK_SURVEY_SECTIONS: SurveySection[] = [
  {
    id: 'onboarding',
    title: "חלק א': מסכי הפתיחה וההיכרות (Onboarding)",
    questions: [
      {
        key: 'onboarding_welcome',
        title: 'חוויית הכניסה ויצירת סביבה בטוחה',
        allowOther: true,
        options: [
          {
            value: 'excellent',
            label: 'מצוין – העיצוב והטקסטים יצרו מיד תחושה עוטפת, בטוחה ומזמינה.',
          },
          {
            value: 'good_but_technical',
            label: 'טוב, אבל הזרימה הרגישה קצת טכנית או תכליתית מדי לתחילת אימון.',
          },
          {
            value: 'overwhelming',
            label: 'עמוס מדי – כמות המידע או המבנה במסכים הראשונים מעט מציפים.',
          },
          {
            value: 'weak',
            label: 'חלש – הכניסה הרגישה קרה ולא שידרה את התחושה הנדרשת.',
          },
        ],
      },
      {
        key: 'onboarding_intake',
        title: 'איסוף מידע ראשוני (Intake)',
        allowOther: true,
        options: [
          {
            value: 'accurate',
            label: 'מדויק לחלוטין – השאלות נכונות, בונות הקשר, ודורשות מאמץ סביר.',
          },
          {
            value: 'long_tiring',
            label: 'ארוך ומעייף – יש שם שאלות שעדיף לשמור לשלב מאוחר יותר או לוותר עליהן.',
          },
          {
            value: 'intrusive',
            label: 'חודרני/מרתיע – בקשת המידע עלולה לגרום למתאמן לחוסר נוחות.',
          },
          {
            value: 'missing_info',
            label: 'חסר מידע – לדעתי חסרות שאלות היכרות בסיסיות נוספות.',
          },
        ],
      },
    ],
  },
  {
    id: 'stages',
    title: 'חלק ב\': הערכת שלבי "תהליך השיבה" באפליקציה',
    questions: [
      {
        key: 'stage_life_event',
        title: "'אירוע מהחיים'",
        allowOther: true,
        options: [
          {
            value: 'excellent',
            label: 'מצוין – הניסוח מדויק, מזמין ומסביר היטב מהו האירוע הנדרש.',
          },
          {
            value: 'needs_clarification',
            label: 'דורש חידוד – חסר הסבר קצר או דוגמה ל"אירוע מתאים".',
          },
          {
            value: 'too_open',
            label: 'כללי / פתוח מדי – סכנה שהמתאמן ישתף בתחושה כללית במקום בסיטואציה ספציפית.',
          },
          {
            value: 'too_rigid',
            label: 'נוקשה / טכני מדי – הדרך שבה האפליקציה מבקשת את התיאור גורמת לפיזור.',
          },
        ],
      },
      {
        key: 'stage_present_gap',
        title: 'שלב זיהוי המצוי ותפעול הפער',
        allowOther: true,
        options: [
          {
            value: 'very_accurate',
            label: 'מדויק מאוד – שהייה בקושי בצורה אותנטית, שאלות האמונה וההזדמנות ברוח השיטה.',
          },
          {
            value: 'rushing_to_solutions',
            label: 'בריחה לפתרונות – דילוג מהיר מדי על כאב ה"מצוי" לעבר ה"רצוי".',
          },
          {
            value: 'missed_belief_nuance',
            label: 'פספוס הניואנס האמוני – שאלות האמונה/הזדמנות הרגישו מאולצות או לא מותאמות.',
          },
          {
            value: 'stayed_cognitive',
            label: 'הישארות בשכל במקום ברגש – המענה נשאר ברמה הקוגניטיבית ללא חיבור רגשי.',
          },
        ],
      },
      {
        key: 'stage_pattern',
        title: 'זיהוי הדפוס (המעשה החוזר)',
        allowOther: true,
        options: [
          {
            value: 'very_accurate',
            label: 'מדויק מאוד – זיהוי ה"מה" (הפעולה) והמשגה נכונה של הדפוס.',
          },
          {
            value: 'too_technical',
            label: 'תיאור טכני מדי – נשאר ברמת תיאור האירוע ללא המשגה של דפוס רחב.',
          },
          {
            value: 'unclear',
            label: 'חוסר בהירות – בלבול בין רגש לפעולה המונע זיהוי דפוס.',
          },
        ],
      },
      {
        key: 'stage_paradigm',
        title: 'חשיפת הפרדיגמא',
        allowOther: true,
        options: [
          {
            value: 'very_accurate',
            label: 'מדויק מאוד – חשיפת ה"היגיון" המפעיל (מחשבת המעשה) והבנה עמוקה.',
          },
          {
            value: 'stayed_at_excuse',
            label: 'נשאר ברמת התירוץ – הסתפקות בתירוץ השכלי ללא חשיפת הפרדיגמא האמיתית.',
          },
          {
            value: 'too_fast',
            label: 'קפיצה מהירה מדי – חוסר זמן לעיכול הקשר בין המחשבה למעשה.',
          },
        ],
      },
      {
        key: 'stage_position',
        title: 'גילוי העמדה (שורש השינוי)',
        allowOther: true,
        options: [
          {
            value: 'very_accurate',
            label: 'מדויק מאוד – רגע של "אסימון שנופל" ונגיעה בניואנס פנימי מדויק.',
          },
          {
            value: 'cold_analysis',
            label: 'ניתוח שכלי קר – עמדה נכונה לוגית ללא רטט וחיבור רגשי עמוק.',
          },
          {
            value: 'missed_root',
            label: 'פספוס השורש – הסתפקות בשיקוף רגשות/סיסמה ללא ירידה קומה פנימה.',
          },
        ],
      },
      {
        key: 'stage_source_nature',
        title: 'גילוי המקור והטבע (יצירת הכמ"ז)',
        allowOther: true,
        options: [
          {
            value: 'empowering',
            label: 'מעצים וברור – הכמ"ז מרגיש כמו כלי עבודה יישומי.',
          },
          {
            value: 'technical_application',
            label: 'יישום טכני – המושגים הוסברו היטב אך היישום הרגיש מנותק.',
          },
          {
            value: 'unclear_ui',
            label: 'חסרה בהירות טכנית/עיצובית – סכנת איבוד ידיים ורגליים במסך.',
          },
          {
            value: 'not_personal',
            label: 'לא נגע בייחודיות – לא הפך לכלי משמעותי עבור המתאמן.',
          },
        ],
      },
      {
        key: 'stage_new_position',
        title: 'שלב בחירת עמדה חדשה',
        allowOther: true,
        options: [
          {
            value: 'deep_invitation',
            label: 'בהחלט – הזמנה אמיתית לשינוי עמוק ומתוך בחירה.',
          },
          {
            value: 'lacking_emotional_depth',
            label: 'חסר עומק רגשי – תהליך זורם אך לא הרגיש כשינוי פנימי מהותי.',
          },
          {
            value: 'intellectual_solution',
            label: 'פתרון שכלי – הרגיש יותר כפתרון לוגי מאשר שינוי עמדה.',
          },
          {
            value: 'unclear_flow',
            label: 'זרימה לא ברורה – הממשק במסך הפריע לחוויה.',
          },
        ],
      },
      {
        key: 'stage_new_paradigm_pattern',
        title: 'בחירת פרדיגמא ודפוס חדשים',
        allowOther: true,
        options: [
          {
            value: 'excellent',
            label: 'מעולה – תרגום חלק של העמדה החדשה לפעולות מעשיות.',
          },
          {
            value: 'confusing_distinction',
            label: 'הבחנה מבלבלת – הקושי להבדיל בין פרדיגמא לדפוס בממשק הנוכחי.',
          },
          {
            value: 'shallow_prompts',
            label: 'הצעות שטחיות – שאלות ההכוונה לא היו מספיק עמוקות.',
          },
          {
            value: 'disconnected_from_kamz',
            label: 'חסר חיבור לכמ"ז – ניתוק בין הבחירות החדשות למהות המתאמן.',
          },
        ],
      },
      {
        key: 'stage_commitment',
        title: 'צומת הבחירה והבקשה לאימון',
        allowOther: true,
        options: [
          {
            value: 'powerful_closing',
            label: 'סיום עוצמתי – העברת אחריות מלאה למתאמן והנעה לשינוי.',
          },
          {
            value: 'term_not_accessible',
            label: 'מושג לא מונגש – המונח "בקשה לאימון" לא הוטמע כפעולה מעשית ומדידה.',
          },
          {
            value: 'disconnected',
            label: 'חוסר רצף ותלישות – איסוף הנתונים הרגיש מנותק מעומק התהליך.',
          },
          {
            value: 'overwhelming',
            label: 'עומס והצפה – מסך עמוס ומבלבל ברגע שדורש שקט פנימי.',
          },
        ],
      },
    ],
  },
  {
    id: 'experience',
    title: 'חלק ג\': חוויית האימון ורוח השיטה',
    questions: [
      {
        key: 'coaching_spirit',
        title: 'רוח וערכי האימון היהודי',
        allowOther: true,
        options: [
          { value: 'fully_reflected', label: 'שיקפו לחלוטין.' },
          { value: 'partially_reflected', label: 'שיקפו חלקית.' },
          {
            value: 'too_technical',
            label: 'החוויה הרגישה טכנית ורובוטית מדי.',
          },
        ],
      },
      {
        key: 'session_end_feeling',
        title: 'התחושה בסיום הסשן',
        allowOther: true,
        options: [
          { value: 'relief_clarity', label: 'הקלה / סדר בראש.' },
          { value: 'motivation', label: 'מוטיבציה לפעולה.' },
          { value: 'confusion', label: 'בלבול.' },
          { value: 'frustration', label: 'תסכול (מענה לא מדויק).' },
        ],
      },
    ],
  },
];

export const RECOMMEND_TRAINEES_OPTIONS: SurveyChoiceOption[] = [
  { value: 'yes', label: 'כן, בפירוש.' },
  { value: 'maybe', label: 'אולי, תלוי בשלב האימוני.' },
  { value: 'no', label: 'לא, לדעתי זה עשוי להפריע לתהליך.' },
];

export const REQUIRED_CHOICE_KEYS = [
  ...COACH_FEEDBACK_SURVEY_SECTIONS.flatMap((section) =>
    section.questions.map((question) => question.key),
  ),
  'recommend_trainees',
] as const;
