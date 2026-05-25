export type SurveyChoiceOption = {
  value: string;
  label: string;
};

export type SurveyQuestion = {
  key: string;
  number?: number;
  subsection?: string;
  title: string;
  description?: string;
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
  'ראשית תודה על הזמן שאתם מקדישים להתנסות במערכת שלנו! כאנשי מקצוע, חוות הדעת שלכם היא החוליה החסרה והחשובה ביותר. מטרת ההתנסות היא לבחון עד כמה האפליקציה מצליחה להעביר תהליך אימוני אותנטי, עמוק ואפקטיבי, תוך נאמנות מירבית למתודולוגיה של "תהליך השיבה".\n\nנודה לכם על כנות מקסימלית – גם ובעיקר אם יש דברים שטעונים שיפור קטן כגדול!';

export const COACH_FEEDBACK_SURVEY_THANK_YOU =
  'תודה רבה על השקעת הזמן והמחשבה!';

export const QUESTION_QUALITY_PROMPT =
  'האם זכורה לך שאלה ספציפית שהייתה מצוינת, או לחלופין שאלה שפספסה לחלוטין את המטרה?';

export const UPGRADE_SUGGESTION_PROMPT =
  'לו היית יכול/ה לשנות, להוסיף או להוריד דבר אחד באפליקציה שיקפיץ דרמטית את הערך שלה, מה זה היה?';

export const UPGRADE_SUGGESTION_HINT = 'אם יש יותר מאחד – נשמח שתכתוב.';

export const RECOMMEND_TRAINEES_PROMPT =
  'האם היית ממליץ/ה למתאמנים שלך להשתמש בכלי כזה בין המפגשים איתך?';

export const RECOMMEND_REASON_PROMPT = 'מדוע?';

export const COACH_FEEDBACK_SURVEY_SECTIONS: SurveySection[] = [
  {
    id: 'onboarding',
    title: "חלק א': מסכי הפתיחה וההיכרות (Onboarding)",
    questions: [
      {
        key: 'onboarding_welcome',
        number: 1,
        title: 'חוויית הכניסה ויצירת סביבה בטוחה',
        description:
          'הכניסה לאפליקציה אמורה לדמות תחילת מפגש אימוני, בו נוצרים יחסי אמון וסביבה מאפשרת. עד כמה מסכי הפתיחה הצליחו להשרות תחושה של ביטחון, מקצועיות ועין טובה?',
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
            label:
              'עמוס מדי – כמות המידע או המבנה במסכים הראשונים מעט מציפים ומקשים על המיקוד.',
          },
          {
            value: 'weak',
            label: 'חלש – הכניסה הרגישה קרה ולא שידרה את התחושה הנדרשת.',
          },
        ],
      },
      {
        key: 'onboarding_intake',
        number: 2,
        title: 'איסוף מידע ראשוני (Intake)',
        description:
          'במסכי הפתיחה המערכת מבקשת מהמתאמן לספק מידע בסיסי על עצמו לפני הכניסה לתהליך עצמו. האם סוג וכמות השאלות בשלב זה נכונים, או שהם עלולים לייצר התנגדות?',
        allowOther: true,
        options: [
          {
            value: 'accurate',
            label: 'מדויק לחלוטין – השאלות נכונות, בונות הקשר, ודורשות מאמץ סביר.',
          },
          {
            value: 'long_tiring',
            label:
              'ארוך ומעייף – יש שם שאלות (או עודף שאלות) שעדיף לשמור לשלב מאוחר יותר או לוותר עליהן.',
          },
          {
            value: 'intrusive',
            label:
              'חודרני/מרתיע – בקשת המידע הספציפי בשלב הזה עלולה לגרום למתאמן לחוסר נוחות או לנטוש.',
          },
          {
            value: 'missing_info',
            label:
              'חסר מידע – לדעתי חסרות שאלות היכרות בסיסיות נוספות שהיו עוזרות לדייק את המשך הסשן.',
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
        number: 3,
        title: "'אירוע מהחיים'",
        description:
          'בשלב שבו האפליקציה מבקשת מהמתאמן לשתף באירוע (הסיטואציה), האם ההכוונה הייתה ברורה ומדויקת מספיק כדי שהמתאמן יבין בדיוק לאיזה סוג של אירוע המערכת מתכוונת ומה עליו לשתף?',
        allowOther: true,
        options: [
          {
            value: 'excellent',
            label: 'מצוין – הניסוח מדויק, מזמין, ומסביר היטב מהו האירוע הנדרש.',
          },
          {
            value: 'needs_clarification',
            label:
              'דורש חידוד – ההנחיה קיימת, אך חסר הסבר קצר או דוגמה שיעזרו למתאמן להבין מה נחשב ל"אירוע מתאים לתהליך השיבה".',
          },
          {
            value: 'too_open',
            label:
              'כללי / פתוח מדי – ההכוונה לא מספיק ברורה, ויש סכנה שהמתאמן ישתף רק בתחושה כללית במקום בסיטואציה ספציפית שעליה ניתן לעבוד או ברגע שהתרחש בינו לבין עצמו.',
          },
          {
            value: 'too_rigid',
            label:
              'נוקשה / טכני מדי – הדרך שבה האפליקציה מבקשת את תיאור האירוע לא מספיק ברורה וגורמת לפיזור ודישדוש במקום.',
          },
        ],
      },
      {
        key: 'stage_present_gap',
        number: 4,
        title: 'שלב זיהוי המצוי ותפעול הפער',
        description:
          'עד כמה האפליקציה אפשרה למתאמן לשהות ב"פער" ולעבד את המצוי בצורה מדויקת ומעצימה (כולל שאלות האמונה וההזדמנות)?',
        allowOther: true,
        options: [
          {
            value: 'very_accurate',
            label:
              'מדויק מאוד – האפליקציה אפשרה למתאמן לשהות בקושי בצורה אותנטית, ושאלות האמונה וההזדמנות נוסחו בדיוק ברוח השיטה.',
          },
          {
            value: 'rushing_to_solutions',
            label:
              'בריחה לפתרונות – האפליקציה דילגה מהר מדי על כאב ה"מצוי" וניסתה לדחוף את המתאמן לעבר פתרונות או ל"רצוי" לפני ששהה בפער.',
          },
          {
            value: 'missed_belief_nuance',
            label:
              'פספוס הניואנס האמוני – שאלות האמונה ("האם אתה מאמין ש...") או ההזדמנות הרגישו מאולצות, טכניות או לא מותאמות לעוצמת הסיטואציה שהמתאמן העלה.',
          },
          {
            value: 'stayed_cognitive',
            label:
              'הישארות בשכל במקום ברגש – המענה נשאר ברמה השכלית (הקוגניטיבית) של תיאור הסיטואציה, ולא באמת עזר למתאמן להתחבר לכאב או לקושי הרגשי.',
          },
        ],
      },
      {
        key: 'stage_pattern',
        number: 5,
        subsection: 'שלב ההרחבה והעמקה',
        title: 'זיהוי הדפוס (המעשה החוזר)',
        description:
          'עד כמה האפליקציה הצליחה לסייע למתאמן לזהות את הדפוס שחוזר על עצמו בסיטואציה בצורה ברורה?',
        allowOther: true,
        options: [
          {
            value: 'very_accurate',
            label:
              'מדויק מאוד – האפליקציה זיהתה היטב את ה"מה" (הפעולה) והצליחה למהשיג את הדפוס בצורה שפגשה את המציאות של המתאמן.',
          },
          {
            value: 'too_technical',
            label:
              'תיאור טכני מדי – הזיהוי נשאר ברמת תיאור האירוע ולא הצליח להפוך ל"המשגה" של דפוס רחב יותר שחוזר בחיים.',
          },
          {
            value: 'unclear',
            label:
              'חוסר בהירות – הניסוח של האפליקציה בלבל את המתאמן בין מה שהוא מרגיש לבין מה שהוא עושה, והוא לא הצליח לזהות את הדפוס.',
          },
        ],
      },
      {
        key: 'stage_paradigm',
        number: 6,
        title: 'חשיפת הפרדיגמא',
        description: 'במעבר מהדפוס אל הפרדיגמא – האם ההכוונה הייתה מדויקת?',
        allowOther: true,
        options: [
          {
            value: 'very_accurate',
            label:
              'מדויק מאוד – האפליקציה חשפה בצורה מרשימה את ה"היגיון" שמפעיל את הדפוס (מחשבת המעשה) ויצרה הבנה קוגניטיבית עמוקה.',
          },
          {
            value: 'stayed_at_excuse',
            label:
              'נשאר ברמת התירוץ – האפליקציה הסתפקה בתירוץ השכלי של המתאמן ולא הצליחה לחשוף את ה"פרדיגמא" האמיתית שמנהלת אותו.',
          },
          {
            value: 'too_fast',
            label:
              'קפיצה מהירה מדי – המעבר מהדפוס לפרדיגמא היה מהיר מדי ולא נתן למתאמן זמן לעכל את הקשר בין המחשבה למעשה.',
          },
        ],
      },
      {
        key: 'stage_position',
        number: 7,
        title: 'גילוי העמדה (שורש השינוי)',
        description: 'האם האפליקציה הצליחה לחדור מבעד לשכבות ולחשוף את העמדה?',
        allowOther: true,
        options: [
          {
            value: 'very_accurate',
            label:
              'מדויק מאוד – זה היה רגע של "אסימון שנופל"; האפליקציה נגעה בשורש העומק (העמדה) ופגשה ניואנס פנימי מדויק.',
          },
          {
            value: 'cold_analysis',
            label:
              'ניתוח שכלי קר – האפליקציה כיוונה ל"עמדה" שנשמעה נכונה לוגית, אבל היא לא יצרה רטט וחיבור רגשי עמוק אצל המתאמן.',
          },
          {
            value: 'missed_root',
            label:
              'פספוס השורש – האפליקציה הסתפקה בשיקוף רגשות או בסיסמה כללית, ולא אתגרה את המתאמן לרדת באמת עוד קומה פנימה אל עבר העמדה שמנהלת אותו.',
          },
        ],
      },
      {
        key: 'stage_source_nature',
        number: 8,
        title: 'שלב גילוי המקור והטבע (יצירת הכמ"ז)',
        description:
          'איך חווית את תהליך זיקוק כוחות ה"מקור" וה"טבע" ובניית הכמ"ז (כרטיס מהות-זהות) דרך האפליקציה?',
        allowOther: true,
        options: [
          {
            value: 'empowering',
            label: 'מעצים וברור – הכמ"ז מרגיש כמו כלי עבודה יישומי שהלקוח לוקח איתו.',
          },
          {
            value: 'concepts_explained_disconnected',
            label:
              'המושגים הוסברו היטב, אבל היישום שלהם באפליקציה הרגיש קצת מנותק או טכני.',
          },
          {
            value: 'unclear_ui',
            label:
              'חסרה בהירות טכנית/עיצובית במסך הזה – המתאמן עלול ללכת בו לאיבוד.',
          },
          {
            value: 'missed_uniqueness',
            label:
              'לא הצליח לגעת בייחודיות האמיתית של המתאמן ולהפוך לכלי משמעותי.',
          },
        ],
      },
      {
        key: 'stage_new_position',
        number: 9,
        title: 'שלב בחירת עמדה חדשה',
        description:
          'האם האפליקציה הצליחה להביא את המתאמן למקום שמאפשר בחירת "עמדה חדשה" באמת?',
        allowOther: true,
        options: [
          {
            value: 'deep_invitation',
            label: 'בהחלט – הורגשה הזמנה אמיתית לשינוי עמוק ומתוך בחירה.',
          },
          {
            value: 'lacking_emotional_depth',
            label:
              'התהליך היה זורם, אך חסר קצת עומק רגשי כדי שזה ירגיש כמו שינוי עמדה פנימי ומהותי.',
          },
          {
            value: 'intellectual_solution',
            label: 'זה הרגיש יותר כמו בחירת "פתרון שכלי" מאשר שינוי עמדה עמוק.',
          },
          {
            value: 'unclear_flow',
            label: 'הזרימה במסך הזה הייתה לא ברורה והפריעה לחוויה.',
          },
        ],
      },
      {
        key: 'stage_new_paradigm_pattern',
        number: 10,
        title: 'שלב בחירת פרדיגמא ודפוס חדשים',
        description:
          'בשלב התרגום למעשה – בחירת הפרדיגמא והדפוס החדש – עד כמה ההכוונה הייתה מדויקת ויישומית?',
        allowOther: true,
        options: [
          {
            value: 'excellent',
            label: 'מעולה – עזר לתרגם את העמדה החדשה לפעולות מעשיות בצורה חלקה.',
          },
          {
            value: 'confusing_distinction',
            label:
              'ההבחנה בין יצירת פרדיגמא חדשה לדפוס חדש עשויה לבלבל את המשתמש בממשק הנוכחי.',
          },
          {
            value: 'shallow_prompts',
            label: 'ההצעות או שאלות ההכוונה של המערכת היו שטחיות מדי בשלב זה.',
          },
          {
            value: 'disconnected_from_kamz',
            label: 'היה חסר חיבור מורגש בין הבחירות החדשות האלו לבין הכמ"ז של המתאמן.',
          },
        ],
      },
      {
        key: 'stage_commitment',
        number: 11,
        title: 'שלב צומת הבחירה והבקשה לאימון',
        description:
          'איך היית מעריך/ה את סיום התהליך – היציאה לפעולה, הבחירה בצומת וניסוח "הבקשה לאימון"?',
        allowOther: true,
        options: [
          {
            value: 'powerful_closing',
            label:
              'סיום עוצמתי – מעביר את מלוא האחריות למתאמן ומייצר בו רצון לנוע קדימה לשינוי.',
          },
          {
            value: 'term_not_accessible',
            label:
              'מושג לא מונגש – המושג "בקשה לאימון" לא הוסבר או הוטמע בצורה שמניעה לפעולה מעשית ומדידה.',
          },
          {
            value: 'disconnected',
            label:
              'חוסר רצף ותלישות – הניסיון לאסוף את נתוני התהליך לתוך ניסוח הבקשה הרגיש מנותק וטכני, ולא שיקף את העומק של מה שהמתאמן עבר עד לאותה נקודה.',
          },
          {
            value: 'overwhelming',
            label:
              'עומס והצפה במסך – הניסיון להציג את צומת הבחירות ולגזור ממנו פעולה מייצר מסך עמוס ומבלבל, בדיוק ברגע שבו נדרש שקט פנימי לסיכום.',
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
        number: 12,
        title: 'רוח וערכי האימון היהודי',
        description:
          'האם השפה, הניסוחים והטון של האפליקציה שיקפו בעיניך את הסגנון והייחודי של האימון היהודי?',
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
        number: 13,
        title: 'התחושה בסיום הסשן',
        description: 'מהי התחושה המרכזית שאיתה סיימת את הסשן באפליקציה?',
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
  { value: 'maybe', label: 'אולי, תלוי בשלב האימוני של המתאמן.' },
  { value: 'no', label: 'לא, לדעתי זה עשוי להפריע לתהליך האישי.' },
];

export const REQUIRED_CHOICE_KEYS = [
  ...COACH_FEEDBACK_SURVEY_SECTIONS.flatMap((section) =>
    section.questions.map((question) => question.key),
  ),
  'recommend_trainees',
] as const;
