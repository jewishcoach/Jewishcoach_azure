/**
 * Privacy policy copy for Jewish Coach AI (BSD coaching web app).
 * Hebrew + English; keep in sync when updating legal text.
 */

export type PrivacySection = {
  id: string;
  title: string;
  paragraphs: string[];
};

export const PRIVACY_SECTIONS_HE: PrivacySection[] = [
  {
    id: 'intro',
    title: 'מבוא',
    paragraphs: [
      'מדיניות פרטיות זו מתארת כיצד אנו מטפלים במידע אישי במסגרת שירות "מאמן יהודי AI" (להלן: "השירות") — אפליקציית אימון מקוונת המבוססת על שיטת האימון היהודי (BSD), הכוללת שיחות עם מאמן וירטואלי, ניהול פרופיל, דשבורד, תזכורות ויכולות נלוות.',
      'השימוש בשירות מהווה הסכמה לעיבוד מידע כמפורט להלן. אם אינך מסכים — הנא להימנע משימוש בשירות.',
    ],
  },
  {
    id: 'controller',
    title: 'מפעיל השירות',
    paragraphs: [
      'השירות מופעל באמצעות מערכת טכנולוגית (אחסון בענן, מסד נתונים וממשק משתמש) המיועדת לספק את חוויית האימון. לשאלות בנוגע למדיניות זו ניתן לפנות דרך ערוצי התמיכה שיפורסמו באפליקציה או באתר, או בכתובת דוא"ל: support@jewishcoacher.com (ככל שהכתובת פעילה).',
    ],
  },
  {
    id: 'collected',
    title: 'איזה מידע נאסף',
    paragraphs: [
      'חשבון והזדהות: בעת הרשמה והתחברות נעשה שימוש בשירות הזדהות (כגון Clerk) לאימות דוא"ל וניהול חשבון. ייתכן שנשמרו שם תצוגה, כתובת דוא"ל ומזהים טכניים הנדרשים לפעולת החשבון.',
      'תוכן אימון: הודעות שאתה שולח ותגובות המאמן נשמרות כדי לאפשר המשך שיחה, היסטוריה ותכונות דשבורד (סטטיסטיקות, יומן, תזכורות וכו׳). התוכן עשוי לכלול מידע רגיש שתבחר לשתף במסגרת תהליך האימון.',
      'נתוני שימוש וחיוב: ייתכן שנאסוף נתוני שימוש כגון מספר הודעות בתקופת חיוב, שימוש בתכונות קוליות (לפי תוכנית המנוי), ומזהים טכניים לצורך אבטחה ומניעת שימוש לרעה.',
      'הקלטה ותמלול קולי (אופציונלי): אם תפעיל הקלטה מהדפדפן, אודיו עשוי לעבור לשירות זיהוי דיבור (למשל Microsoft Azure Speech) לצורך המרה לטקסט. אנו לא משתמשים בהקלטה למטרות פרסום; העיבוד נועד לאפשר הזנת טקסט בשיחה.',
      'יומן ויומן שיעורים: אם תשתמש בתכונות יומן או תזכורות, ייתכן שיישמרו אירועים ותזכורות שתזין, וכן חיבורים אופציונליים לשירותי לוח שנה חיצוניים — בהתאם להרשאות שתעניק.',
    ],
  },
  {
    id: 'purposes',
    title: 'מטרות העיבוד',
    paragraphs: [
      'מתן השירות והפעלת האימון (שיחות, שמירת היסטוריה, דשבורד).',
      'אבטחה, מניעת הונאה ועמידה במגבלות שימוש לפי תוכנית מנוי.',
      'שיפור יציבות ואיכות השירות (למשל לוגים טכניים).',
    ],
  },
  {
    id: 'processors',
    title: 'ספקים ושירותי צד שלישי',
    paragraphs: [
      'השירות עשוי להסתמך על ספקי תשתית ובינה מלאכותית, לרבות: ספק זהות והתחברות (Clerk), ספקי ענן ומסדי נתונים (למשל Microsoft Azure), מודלי שפה לצורך תגובות המאמן (למשל Azure OpenAI), ושירותי דיבור (Azure Speech) לתמלול. הספקים מקבלים רק את המידע הנדרש להפעלת השירות, כפי שמקובל בספקי SaaS.',
      'עיבוד נתונים בחו"ל: חלק מהספקים עשויים לאחסן או לעבד מידע מחוץ לישראל. בשימוש בשירות אתה מודע לכך. מומלץ לעיין גם במדיניות הפרטיות של Clerk ושל Microsoft.',
    ],
  },
  {
    id: 'security',
    title: 'אבטחה',
    paragraphs: [
      'אנו פועלים להגנה סבירה על המידע, לרבות שימוש בתעבורה מוצפנת (HTTPS) ובקרות גישה. אין מערכת חסינה לחלוטין; יש לשמור על סודיות פרטי ההתחברות שלך.',
    ],
  },
  {
    id: 'retention',
    title: 'שמירת מידע',
    paragraphs: [
      'תוכן השיחות והפרופיל נשמרים כל עוד החשבון פעיל ולפי הצורך התפעולי. מחיקת חשבון או בקשת מחיקה — ככל שתינתן בממשק או בפנייה לתמיכה — תטופל בהתאם למדיניות העדכנית ולדין החל.',
    ],
  },
  {
    id: 'rights',
    title: 'זכויותיך',
    paragraphs: [
      'בהתאם לחוק הגנת הפרטיות, התשמ"א–1981, ולתקנות הנלוות, ייתכן שתהיה זכות לעיין במידע, לבקש תיקון או מחיקה, ולבקש להגביל עיבוד — כפי שיחול בנסיבות העניין. ניתן לפנות לתמיכה בבקשות מסוג זה. ייתכנו יוצאים מהכלל לפי דין (למשל חובות שמירה משפטית).',
    ],
  },
  {
    id: 'children',
    title: 'קטינים',
    paragraphs: [
      'השירות אינו מיועד לילדים מתחת לגיל 13. אם אתה הורה או אפוטרופוס וגילית שנאסף מידע על קטין שלא כדין — אנא פנה אלינו.',
    ],
  },
  {
    id: 'changes',
    title: 'שינויים במדיניות',
    paragraphs: [
      'ייתכן שנעדכן מדיניות זו מעת לעת. עדכון מהותי יתואר באפליקציה או בדף זה, עם תאריך עדכון מתחת. המשך שימוש לאחר עדכון עשוי להוות הסכמה לגרסה המעודכנת, ככל שהדין מתיר.',
    ],
  },
];

export const PRIVACY_SECTIONS_EN: PrivacySection[] = [
  {
    id: 'intro',
    title: 'Introduction',
    paragraphs: [
      'This Privacy Policy describes how we handle personal information in the "Jewish Coach AI" service (the "Service") — a web application for Jewish Coaching (BSD), including conversations with a virtual coach, profile management, dashboard features, reminders, and related capabilities.',
      'By using the Service you agree to the processing described below. If you do not agree, please do not use the Service.',
    ],
  },
  {
    id: 'controller',
    title: 'Service operator',
    paragraphs: [
      'The Service is operated through cloud-hosted infrastructure (database, APIs, and client app) intended to deliver the coaching experience. For questions about this policy, please use support channels published in the app or website, or email support@jewishcoacher.com (when available).',
    ],
  },
  {
    id: 'collected',
    title: 'Information we collect',
    paragraphs: [
      'Account & authentication: Sign-in may use an identity provider (e.g. Clerk) for email verification and session management. We may store display name, email address, and technical identifiers needed to operate your account.',
      'Coaching content: Messages you send and coach responses are stored to enable ongoing conversations, history, and dashboard features (statistics, journal, reminders, etc.). Content may include sensitive information you choose to share during coaching.',
      'Usage & billing: We may collect usage metrics such as message counts per billing period, optional voice-feature usage (per subscription plan), and technical data for security and abuse prevention.',
      'Voice input & transcription (optional): If you use microphone recording in the browser, audio may be sent to a speech-to-text service (e.g. Microsoft Azure Speech) to convert speech to text. We do not use recordings for advertising; processing is intended to enter text into the chat.',
      'Calendar & reminders: If you use calendar or reminder features, events and reminders you enter may be stored, along with optional connections to external calendar services — according to permissions you grant.',
    ],
  },
  {
    id: 'purposes',
    title: 'Purposes of processing',
    paragraphs: [
      'Providing the Service and coaching experience (chat, history, dashboard).',
      'Security, fraud prevention, and enforcing plan limits.',
      'Service reliability and quality (e.g. technical logs).',
    ],
  },
  {
    id: 'processors',
    title: 'Sub-processors and third-party services',
    paragraphs: [
      'The Service may rely on infrastructure and AI providers, including: identity/sign-in (Clerk), cloud hosting and databases (e.g. Microsoft Azure), language models for coach responses (e.g. Azure OpenAI), and speech services (Azure Speech) for transcription. Providers receive only data needed to operate the Service, as is standard for SaaS.',
      'International processing: Some providers may store or process data outside Israel. By using the Service you acknowledge this. We encourage you to review Clerk’s and Microsoft’s privacy notices.',
    ],
  },
  {
    id: 'security',
    title: 'Security',
    paragraphs: [
      'We apply reasonable safeguards, including encrypted transport (HTTPS) and access controls. No system is perfectly secure; please protect your login credentials.',
    ],
  },
  {
    id: 'retention',
    title: 'Retention',
    paragraphs: [
      'Conversation content and profile data are retained while your account is active and as needed for operations. Account deletion or erasure requests — when offered in the product or via support — will be handled according to applicable policy and law.',
    ],
  },
  {
    id: 'rights',
    title: 'Your rights',
    paragraphs: [
      'Depending on applicable law (including Israeli Privacy Protection Law, 5741–1981), you may have rights to access, correct, delete, or restrict processing of your personal data. Contact support for such requests. Exceptions may apply (e.g. legal retention obligations).',
    ],
  },
  {
    id: 'children',
    title: 'Children',
    paragraphs: [
      'The Service is not directed at children under 13. If you believe we have collected a child’s information improperly, please contact us.',
    ],
  },
  {
    id: 'changes',
    title: 'Changes to this policy',
    paragraphs: [
      'We may update this Privacy Policy from time to time. Material changes will be indicated in the app or on this page with an updated date. Continued use after changes may constitute acceptance of the revised policy where permitted by law.',
    ],
  },
];
