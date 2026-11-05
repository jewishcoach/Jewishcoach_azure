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
      'כרטיסי התהליך: התשובות שתמלא בכרטיסים (האירוע, הרגשות, המחשבה, המעשה, הרצוי, הפער, העמדה, כוחות המקור והטבע, הבקשה לאימון) נשמרות יחד עם השיחה.',
      'ניתוח אישי (בהסכמה בלבד): בסוף תהליך תוכל לבקש מכתב תובנות אישי. הוא נכתב רק אם נתת לכך הסכמה, ורק על סמך השיחה הנוכחית. אפשר לבטל את ההסכמה בכל עת בפנייה לתמיכה.',
      'נתונים טכניים: לכל תגובת מאמן נשמרים זמני עיבוד (באלפיות שנייה), ללא תוכן, לצורך שיפור מהירות השירות.',
    ],
  },
  {
    id: 'couple',
    title: 'תהליך זוגי',
    paragraphs: [
      'בתהליך הזוגי כל אחד מבני הזוג עובד לבד, בשיחה פרטית משלו, על אירוע משותף. בן/בת הזוג אינם רואים את השיחה שלך בשום שלב.',
      'בן/בת הזוג רואים רק את השורות שתבחר לשתף במסכים המשותפים, אחרי תצוגה מקדימה שבה תוכל לערוך או להסתיר כל שורה. הודעות הדוא"ל בתהליך (הזמנה, עדכון) אינן כוללות תוכן מהשיחה.',
      'אם תמחק שיחה של תהליך זוגי, גם מה ששיתפת יוסר מהמסכים המשותפים והחלק המשותף יסתיים.',
    ],
  },
  {
    id: 'ai',
    title: 'מאמן מבוסס בינה מלאכותית ובטיחות',
    paragraphs: [
      'המאמן בשירות הוא מערכת בינה מלאכותית ולא אדם. הוא אינו מחליף טיפול רגשי, נפשי או רפואי.',
      'כדי לשמור על בטיחותך, הודעות מסוימות נבדקות אוטומטית לזיהוי סימני סיכון (למשל מחשבות על פגיעה עצמית). במקרה כזה תוצג לך הודעה עם קווי סיוע במקום המשך התהליך. הבדיקה אוטומטית ואינה מועברת לגורם אנושי.',
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
      'מיקום המידע: מסד הנתונים של השירות מאוחסן ב-Microsoft Azure באזור קנדה (טורונטו), ברשת פרטית שאינה נגישה מהאינטרנט. שרתי השירות ומודל השפה פועלים ב-Microsoft Azure בארה"ב. כלומר, המידע מאוחסן ומעובד מחוץ לישראל.',
      'לפי תנאי Microsoft לשירות Azure OpenAI, תוכן השיחות אינו משמש לאימון מודלי השפה. מומלץ לעיין גם במדיניות הפרטיות של Clerk ושל Microsoft.',
    ],
  },
  {
    id: 'security',
    title: 'אבטחה',
    paragraphs: [
      'אנו פועלים להגנה סבירה על המידע, לרבות שימוש בתעבורה מוצפנת (HTTPS) ובקרות גישה. אין מערכת חסינה לחלוטין; יש לשמור על סודיות פרטי ההתחברות שלך.',
      'גישה של צוות השירות לתוכן שיחות נעשית רק כשהיא נדרשת לטיפול בתקלה, לבטיחות או לבקשת תמיכה, ובהיקף המינימלי הנדרש.',
    ],
  },
  {
    id: 'retention',
    title: 'שמירת מידע',
    paragraphs: [
      'תוכן השיחות והפרופיל נשמרים כל עוד החשבון פעיל, או עד שתמחק אותם.',
      'מחיקת שיחה: בתפריט, ברשימת "השיחות שלי", אפשר למחוק כל שיחה. המחיקה כוללת את ההודעות, הכרטיסים ומכתבי התובנות שנכתבו על סמך השיחה, והיא מיידית במסד הנתונים הפעיל. עותקי גיבוי נשמרים עד 35 יום ואז נמחקים.',
      'מחיקת חשבון: ניתן לבקש מחיקה של החשבון וכל המידע שבו בפנייה לתמיכה (support@jewishcoacher.com).',
    ],
  },
  {
    id: 'rights',
    title: 'זכויותיך',
    paragraphs: [
      'בהתאם לחוק הגנת הפרטיות, התשמ"א–1981, ולתקנות הנלוות, ייתכן שתהיה זכות לעיין במידע, לבקש תיקון או מחיקה, ולבקש להגביל עיבוד — כפי שיחול בנסיבות העניין. ניתן לפנות לתמיכה בבקשות מסוג זה. ייתכנו יוצאים מהכלל לפי דין (למשל חובות שמירה משפטית).',
      'חלק מהזכויות ניתן לממש ישירות באפליקציה: מחיקת שיחה (בתפריט), ועדכון השם ואופן הפנייה (בכרטיס "החשבון שלי").',
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
      'Process cards: the answers you enter in the cards (event, emotions, thought, action, desired, gap, stance, source and nature forces, coaching request) are stored with the conversation.',
      'Personal analysis (with consent only): at the end of a process you may ask for a personal insights letter. It is written only if you consented, and only from the current conversation. You can withdraw consent at any time by contacting support.',
      'Technical data: processing times (in milliseconds, no content) are stored for each coach response, to improve the speed of the Service.',
    ],
  },
  {
    id: 'couple',
    title: 'Couple process',
    paragraphs: [
      'In the couple process each partner works alone, in a private conversation, on a shared event. Your partner never sees your conversation.',
      'Your partner sees only the lines you choose to share on the shared screens, after a preview in which you can edit or hide each line. Emails in the process (invitation, updates) contain no conversation content.',
      'If you delete a couple-process conversation, what you shared is removed from the shared screens and the shared part ends.',
    ],
  },
  {
    id: 'ai',
    title: 'AI coach and safety',
    paragraphs: [
      'The coach in the Service is an artificial-intelligence system, not a person. It is not a substitute for emotional, psychological or medical care.',
      'For your safety, some messages are checked automatically for signs of risk (for example thoughts of self-harm). In such a case you are shown a message with help lines instead of the next coaching step. The check is automated and is not passed on to a human.',
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
      'Data location: the Service database is hosted on Microsoft Azure in Canada (Toronto), on a private network not reachable from the internet. The Service servers and the language model run on Microsoft Azure in the United States. Data is therefore stored and processed outside Israel.',
      'Under Microsoft\'s terms for Azure OpenAI, conversation content is not used to train the language models.',
      'We encourage you to review Clerk’s and Microsoft’s privacy notices.',
    ],
  },
  {
    id: 'security',
    title: 'Security',
    paragraphs: [
      'We apply reasonable safeguards, including encrypted transport (HTTPS) and access controls. No system is perfectly secure; please protect your login credentials.',
      'Access by the Service team to conversation content happens only when needed to fix a fault, for safety, or for a support request, and to the minimum extent needed.',
    ],
  },
  {
    id: 'retention',
    title: 'Retention',
    paragraphs: [
      'Conversation content and profile data are retained while your account is active, or until you delete them.',
      'Deleting a conversation: in the menu, under "My conversations", you can delete any conversation. Deletion covers its messages, cards and the insight letters written from it, and is immediate in the live database. Backup copies are kept for up to 35 days and then erased.',
      'Deleting your account: you can ask to delete your account and all its data by contacting support (support@jewishcoacher.com).',
    ],
  },
  {
    id: 'rights',
    title: 'Your rights',
    paragraphs: [
      'Depending on applicable law (including Israeli Privacy Protection Law, 5741–1981), you may have rights to access, correct, delete, or restrict processing of your personal data. Contact support for such requests. Exceptions may apply (e.g. legal retention obligations).',
      'Some rights can be used directly in the app: deleting a conversation (in the menu), and updating your name and form of address (in "My account").',
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
