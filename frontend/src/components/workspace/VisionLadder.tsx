/**
 * Vision Ladder - לפי חוברת "תהליך השיבה" מהדורה שלישית
 * שלבים כפי שמופיעים בחוברת
 */

// מיפוי שלב נוכחי (S0-S12) → אינדקס שלב בחוברת
const STEP_TO_PHASE: Record<string, number> = {
  S0: 0,                                 // בקשה לאימון
  S1: 1, S2: 1, S3: 1, S4: 1, S5: 1,    // מצוי (כולל שלושה מסכים)
  S6: 3,                                 // פער
  S7: 4,                                 // דפוס
  S8: 6,                                 // עמדה
  S9: 8,                                 // מקור-טבע-שכל (כמ"ז)
  S10: 10,                               // בחירה
  S11: 11, S12: 11,                      // חזון
};

// 12 שלבים לפי החוברת
const PHASES: { id: string; title: string; tooltip: string }[] = [
  { id: 'p0', title: 'בקשה לאימון', tooltip: 'קבלת רשות והסכמה להתחיל את תהליך האימון.' },
  { id: 'p1', title: 'מצוי', tooltip: 'נושא, אירוע, ושלושת המסכים: רגש, מחשבה, מעשה.' },
  { id: 'p2', title: 'רצוי', tooltip: 'איך היית רוצה – פעולה, רגש ומחשבה רצויים.' },
  { id: 'p3', title: 'פער', tooltip: 'ניתוח הפער בין המצוי לרצוי – שם וציון.' },
  { id: 'p4', title: 'דפוס', tooltip: 'זיהוי הדפוס החוזר – איפה עוד זה קורה?' },
  { id: 'p5', title: 'פרדיגמה', tooltip: 'האמונה והתפיסה שמאחורי הדפוס.' },
  { id: 'p6', title: 'עמדה', tooltip: 'רווח והפסד – מה מרוויח ומה מפסיד מהעמדה.' },
  { id: 'p7', title: 'שינוי', tooltip: 'מעבר מהעמדה הישנה לעמדה חדשה.' },
  { id: 'p8', title: 'מקור-טבע-שכל', tooltip: 'כוחות מקור, כוחות טבע – חיבור לכוח הפנימי.' },
  { id: 'p9', title: 'כמ"ז', tooltip: 'כוח, מקור, זהות – בניית כמ"ז.' },
  { id: 'p10', title: 'בחירה', tooltip: 'התחדשות ובחירה חדשה – עמדה, פרדיגמה ודפוס חדשים.' },
  { id: 'p11', title: 'חזון', tooltip: 'חפץ הלב, שליחות, ומחויבות קונקרטית.' },
];

const CREAM_WHITE = '#F5F5F0';

interface VisionLadderProps {
  currentStep: string;
}

export const VisionLadder = ({ currentStep }: VisionLadderProps) => {
  const activePhaseIndex = STEP_TO_PHASE[currentStep] ?? 0;

  return (
    <div className="w-full min-w-[240px] flex flex-col h-full bg-[#020617] py-8 px-5 workspace-ladder" dir="rtl">
      <div className="flex-1 overflow-y-auto overflow-x-visible custom-scrollbar flex flex-col gap-0">
        {PHASES.map((phase, i) => {
          const isActive = i === activePhaseIndex;
          const isPast = i < activePhaseIndex;
          const isLast = i === PHASES.length - 1;
          return (
            <div key={phase.id} className="flex flex-col items-stretch">
              <div
                className="group relative rounded-[4px] px-4 py-3 border transition-all duration-300"
                style={{
                  background: isActive ? 'rgba(212, 175, 55, 0.12)' : 'rgba(255, 255, 255, 0.03)',
                  borderColor: isActive ? 'rgba(212, 175, 55, 0.4)' : 'rgba(255, 255, 255, 0.08)',
                  boxShadow: isActive ? '0 0 12px rgba(212, 175, 55, 0.15)' : 'none',
                }}
              >
                <div
                  className="text-right font-light text-[15px] tracking-[0.06em] leading-snug"
                  style={{
                    color: isActive ? CREAM_WHITE : isPast ? 'rgba(245,245,240,0.6)' : 'rgba(245,245,240,0.35)',
                  }}
                >
                  {phase.title}
                </div>
                <div
                  className="absolute left-full ml-3 top-1/2 -translate-y-1/2 z-[100] opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none p-3 rounded text-[12px] shadow-xl min-w-[180px] max-w-[260px]"
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    lineHeight: 1.55,
                    background: 'rgba(2,6,23,0.98)',
                    border: '0.5px solid rgba(255,255,255,0.12)',
                    color: 'rgba(245,245,240,0.95)',
                  }}
                >
                  {phase.tooltip}
                </div>
              </div>
              {!isLast && (
                <div
                  className="w-[1px] flex-shrink-0 mx-auto"
                  style={{
                    height: 6,
                    background: 'linear-gradient(to bottom, rgba(212, 175, 55, 0.5), rgba(212, 175, 55, 0.2))',
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
