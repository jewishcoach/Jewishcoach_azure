/**
 * Terms of Use for Jewish Coach AI — educational coaching tool (BSD method).
 * Hebrew + English. Not a substitute for licensed therapy; use at your own risk.
 */

export type TermsSection = {
  id: string;
  title: string;
  paragraphs: string[];
};

export const TERMS_SECTIONS_HE: TermsSection[] = [
  {
    id: 'intro',
    title: 'מבוא ומטרת המסמך',
    paragraphs: [
      'תנאי שימוש אלה ("התנאים") חלים על השימוש בשירות "מאמן יהודי AI" (להלן: "השירות") — פלטפורמת אימון מקוונת המבוססת על שיטת האימון היהודי (BSD), הכוללת שיחות עם מודל שפה (בינה מלאכותית) המוצג כמאמן וירטואלי, דשבורד, היסטוריית שיחות ותכונות נלוות.',
      'המסמך נועד להגדיר את מסגרת השימוש המשפטית, להפחית סיכונים משפטיים, ולהבהיר מה השירות אינו מספק. אנא קרא בעיון לפני השימוש המתמשך בשירות.',
    ],
  },
  {
    id: 'not_professional',
    title: 'אין ייעוץ פסיכולוגי, רפואי או משפטי',
    paragraphs: [
      'השירות אינו תחליף לטיפול פסיכולוגי, פסיכיאטרי, ריפוי בעיסוק, ייעוץ משפטי, ייעוץ מקצועי מוסמך או כל שירות בריאות נפש או גוף הניתן על ידי בעל רישיון.',
      'תוכן השיחות, ההצעות והשאלות המוצגות בשירות הן למטרות חינוך, הכוונה כללית ותרגול שיטתי בלבד. אין בדברים הנאמרים או המוצגים בשירות כוונה לייעץ לפעולה קונקרטית מחייבת, ואין לראות בהם הנחיה מקצועית אישית או תוכנית טיפול.',
      'אם אתה חווה מצוקה נפשית, סיכון לעצמך או לאחרים, או מצב רפואי דחוף — פנה מיד לגורם מקצועי מוסמך או לשירותי חירום המתאימים באזורך.',
    ],
  },
  {
    id: 'no_liability',
    title: 'הגבלת אחריות ושימוש על אחריותך',
    paragraphs: [
      'השירות ניתן "כמות שהוא" (As-Is). למרות מאמצים סבירים לשמור על איכות, דיוק וזמינות, איננו מתחייבים שהשירות יהיה נטול שגיאות, רציף או מתאים לכל צורך.',
      'אין לראות במידע או בשיחה בשירות המלצה לביצוע פעולה כלשהי — כולל החלטות אישיות, משפחתיות, עסקיות, רפואיות או משפטיות. כל החלטה שתקבל מבוססת על השירות היא באחריותך בלבד.',
      'במידה המרבית המותרת על פי דין, לא נהיה אחראים לנזק ישיר, עקיף, תוצאתי או מיוחד הנובע מהשימוש או מאי־יכולת להשתמש בשירות, לרבות אובדן רווח, מוניטין או מידע — אלא אם נקבע אחרת בחוק החל ואינו ניתן לשינוי.',
    ],
  },
  {
    id: 'acceptance',
    title: 'הסכמה לתנאים ושימוש מהווה קבלה',
    paragraphs: [
      'בלחיצה על "שלח", בהמשך שימוש בשירות לאחר הצגת התנאים, או בשימוש חוזר בחשבון — אתה מצהיר שקראת והבנת את תנאי השימוש ומדיניות הפרטיות, וכי אתה מסכים להם.',
      'אם אינך מסכים לתנאים — הנא להימנע משימוש בשירות. המשך שימוש לאחר עדכון התנאים ייחשב, ככל שהדין מתיר, כהסכמה לגרסה המעודכנת.',
      'עליך להיות כשיר משפטית לחוזה לפי דין החל עליך. אם אתה משתמש בשירות בשם ארגון, אתה מצהיר שיש לך הרשאה לחייב את הארגון.',
    ],
  },
  {
    id: 'conduct',
    title: 'שימוש מותר ואיסורים',
    paragraphs: [
      'אסור להשתמש בשירות בניגוד לדין, לניסיון פריצה, להפצת תוכן פוגעני או בלתי חוקי, או לשיבוש זמינות השירות למשתמשים אחרים.',
      'אנו רשאים להגביל, להשעות או לסיים גישה במקרים של הפרת תנאים, סיכון לאבטחה או דרישה חוקית.',
    ],
  },
  {
    id: 'changes',
    title: 'עדכונים לתנאים',
    paragraphs: [
      'ייתכן שנעדכן את התנאים מעת לעת. תאריך עדכון אחרון יוצג בעמוד זה. מומלץ לעיין מחדש בעת שינוי מהותי.',
    ],
  },
];

export const TERMS_SECTIONS_EN: TermsSection[] = [
  {
    id: 'intro',
    title: 'Introduction and purpose',
    paragraphs: [
      'These Terms of Use ("Terms") govern your use of "Jewish Coach AI" (the "Service") — an online coaching platform based on the Jewish Coaching (BSD) method, including conversations with a language model presented as a virtual coach, a dashboard, conversation history, and related features.',
      'This document defines the legal framework for use, helps limit certain legal risks, and clarifies what the Service does not provide. Please read carefully before continuing to use the Service.',
    ],
  },
  {
    id: 'not_professional',
    title: 'Not psychological, medical, or legal advice',
    paragraphs: [
      'The Service is not a substitute for psychological or psychiatric care, occupational therapy, legal counsel, other licensed professional services, or any mental or physical health service provided by a qualified provider.',
      'Conversation content, prompts, and outputs are for educational purposes, general orientation, and structured practice only. Nothing in the Service is intended as a binding instruction to take any specific action, and nothing should be treated as personalized professional advice or a treatment plan.',
      'If you are in crisis, at risk of harm to yourself or others, or have a medical emergency, contact a qualified professional or the appropriate emergency services immediately.',
    ],
  },
  {
    id: 'no_liability',
    title: 'Disclaimer of warranties and limitation of liability',
    paragraphs: [
      'The Service is provided "as is." While we strive for quality, accuracy, and availability, we do not warrant that the Service will be error-free, uninterrupted, or suitable for every need.',
      'You should not rely on the Service as a recommendation to perform any act — including personal, family, business, medical, or legal decisions. Any decision you make based on the Service is solely your responsibility.',
      'To the fullest extent permitted by applicable law, we disclaim liability for direct, indirect, consequential, or special damages arising from use or inability to use the Service, including loss of profits, goodwill, or data — unless mandatory law provides otherwise.',
    ],
  },
  {
    id: 'acceptance',
    title: 'Acceptance of the Terms',
    paragraphs: [
      'By clicking "Send", by continuing to use the Service after these Terms (and the Privacy Policy) are presented, or by repeatedly accessing your account, you represent that you have read and understood the Terms and Privacy Policy and agree to them.',
      'If you do not agree, do not use the Service. Continued use after we update the Terms may, where permitted by law, constitute acceptance of the updated version.',
      'You represent that you have legal capacity to enter a binding agreement. If you use the Service on behalf of an organization, you represent that you are authorized to bind that organization.',
    ],
  },
  {
    id: 'conduct',
    title: 'Permitted use and restrictions',
    paragraphs: [
      'You may not use the Service unlawfully, attempt to compromise security, distribute unlawful or abusive content, or disrupt the Service for others.',
      'We may restrict, suspend, or terminate access for violations, security risk, or as required by law.',
    ],
  },
  {
    id: 'changes',
    title: 'Changes to these Terms',
    paragraphs: [
      'We may update these Terms from time to time. The "last updated" date will be shown on this page. Please review periodically, especially after material changes.',
    ],
  },
];
