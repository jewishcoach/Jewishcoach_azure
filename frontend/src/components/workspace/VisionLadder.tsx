/**
 * Vision Ladder - לפי חוברת "תהליך השיבה" מהדורה שלישית
 * שלבים כפי שמופיעים בחוברת
 * לחיצה על שלב – גלילה חכמה להודעה הראשונה באותו שלב
 */

// מיפוי שלב נוכחי (S0-S15) → אינדקס שלב בחוברת
const STEP_TO_PHASE: Record<string, number> = {
  S0: 0,                                 // בקשה לאימון
  S1: 1, S2: 1, S3: 1, S4: 1, S5: 1,    // מצוי (נושא, אירוע, רגש, מחשבה, מעשה)
  S6: 2,                                 // רצוי
  S7: 3,                                 // פער
  S8: 4,                                 // דפוס
  S9: 5,                                 // פרדיגמה
  S10: 6, S11: 6,                       // עמדה+טריגר, רווחים
  S12: 8,                               // כמ"ז (מקור-טבע-שכל)
  S13: 9, S14: 10, S15: 10,             // בחירה, חזון ומחויבות
};

// Reverse: phase index → stage IDs (for scroll-to-phase)
export const PHASE_TO_STAGES: Record<number, string[]> = {
  0: ['S0'],
  1: ['S1', 'S2', 'S3', 'S4', 'S5'],
  2: ['S6'],
  3: ['S7'],
  4: ['S8'],
  5: ['S9'],
  6: ['S10', 'S11'],
  7: [],  // שינוי - no direct stage
  8: ['S12'],
  9: ['S13'],
  10: ['S14', 'S15'],
};

// 11 שלבים לפי החוברת (מקור-טבע-שכל וכמ"ז – אותו שלב)
const PHASES: { id: string; title: string; tooltip: string }[] = [
  { id: 'p0', title: 'בקשה לאימון', tooltip: 'קבלת רשות והסכמה להתחיל את תהליך האימון.' },
  { id: 'p1', title: 'מצוי', tooltip: 'נושא, אירוע, ושלושת המסכים: רגש, מחשבה, מעשה.' },
  { id: 'p2', title: 'רצוי', tooltip: 'איך היית רוצה – פעולה, רגש ומחשבה רצויים.' },
  { id: 'p3', title: 'פער', tooltip: 'ניתוח הפער בין המצוי לרצוי – שם וציון.' },
  { id: 'p4', title: 'דפוס', tooltip: 'זיהוי הדפוס החוזר – איפה עוד זה קורה?' },
  { id: 'p5', title: 'פרדיגמה', tooltip: 'האמונה והתפיסה שמאחורי הדפוס.' },
  { id: 'p6', title: 'עמדה', tooltip: 'רווח והפסד – מה מרוויח ומה מפסיד מהעמדה.' },
  { id: 'p7', title: 'שינוי', tooltip: 'מעבר מהעמדה הישנה לעמדה חדשה.' },
  { id: 'p8', title: 'כמ"ז', tooltip: 'כוח, מקור, זהות – כוחות מקור (ערכים), כוחות טבע (יכולות), חיבור לכוח הפנימי.' },
  { id: 'p9', title: 'בחירה', tooltip: 'התחדשות ובחירה חדשה – עמדה, פרדיגמה ודפוס חדשים.' },
  { id: 'p10', title: 'חזון', tooltip: 'חפץ הלב, שליחות, ומחויבות קונקרטית.' },
];

const CREAM_WHITE = '#F5F5F0';

interface VisionLadderProps {
  currentStep: string;
  onPhaseClick?: (phaseIndex: number) => void;
}

export const VisionLadder = ({ currentStep, onPhaseClick }: VisionLadderProps) => {
  const activePhaseIndex = STEP_TO_PHASE[currentStep] ?? 0;

  return (
    <div className="w-full min-w-[240px] flex flex-col h-full bg-[#1e293b] py-8 px-5 workspace-ladder" dir="rtl">
      <div className="flex-1 overflow-y-auto overflow-x-visible custom-scrollbar flex flex-col gap-0">
        {PHASES.map((phase, i) => {
          const isActive = i === activePhaseIndex;
          const isPast = i < activePhaseIndex;
          const isLast = i === PHASES.length - 1;
          const isClickable = !!onPhaseClick;
          return (
            <div key={phase.id} className="flex flex-col items-stretch">
              <div
                role={isClickable ? 'button' : undefined}
                tabIndex={isClickable ? 0 : undefined}
                aria-label={isClickable ? `${phase.title} - גלילה לחלק זה בשיחה` : undefined}
                onClick={isClickable ? () => onPhaseClick(i) : undefined}
                onKeyDown={isClickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPhaseClick(i); } } : undefined}
                className={`group relative rounded-xl px-4 py-3 border transition-all duration-300 ${isClickable ? 'cursor-pointer hover:bg-white/[0.06]' : 'cursor-default'}`}
                style={{
                  background: isActive ? 'rgba(212, 175, 55, 0.12)' : 'rgba(255, 255, 255, 0.03)',
                  borderColor: isActive ? 'rgba(212, 175, 55, 0.4)' : 'rgba(255, 255, 255, 0.08)',
                  boxShadow: isActive ? '0 0 12px rgba(212, 175, 55, 0.15)' : 'none',
                }}
              >
                <div
                  className="text-center font-light text-[15px] tracking-[0.06em] leading-snug w-full"
                  style={{
                    color: isActive ? CREAM_WHITE : isPast ? 'rgba(245,245,240,0.6)' : 'rgba(245,245,240,0.35)',
                  }}
                >
                  {phase.title}
                </div>
                {/* תיאור שלב - מופיע בריחוף עכבר */}
                <div
                  className="absolute top-full left-1/2 -translate-x-1/2 mt-2 z-[100] opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none p-3 rounded text-[12px] shadow-xl w-[220px] text-right"
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    lineHeight: 1.6,
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
