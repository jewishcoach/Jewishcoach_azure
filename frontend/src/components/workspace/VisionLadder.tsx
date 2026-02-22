const STAGES: { id: string; title: string; tooltip: string }[] = [
  { id: 'S0', title: 'חוזה', tooltip: 'קבלת רשות להתחיל את תהליך האימון' },
  { id: 'S1', title: 'נושא', tooltip: 'הבנת הנושא הכללי' },
  { id: 'S2', title: 'אירוע', tooltip: 'קבלת אירוע ספציפי מפורט' },
  { id: 'S3', title: 'חקירת רגשות', tooltip: 'הצפת רגשות ללא שיפוטיות' },
  { id: 'S4', title: 'מחשבה', tooltip: 'משפט מילולי מדויק באותו רגע' },
  { id: 'S5', title: 'מצוי ורצוי', tooltip: 'סיכום הדפוס' },
  { id: 'S6', title: 'פער', tooltip: 'שם וציון לפער' },
  { id: 'S7', title: 'זיהוי דפוס', tooltip: 'תגובה החוזרת במצבים שונים' },
  { id: 'S8', title: 'רווחים והפסדים', tooltip: 'מה מרוויח ומה מפסיד' },
  { id: 'S9', title: 'ערכים ויכולות', tooltip: 'ערכים חשובים ויכולות קיימות' },
  { id: 'S10', title: 'בחירה', tooltip: 'עמדה חדשה' },
  { id: 'S11', title: 'חזון', tooltip: 'לאן הבחירה מובילה' },
  { id: 'S12', title: 'מחויבות', tooltip: 'פעולה קונקרטית' },
];

const CREAM_WHITE = '#F5F5F0';

interface VisionLadderProps {
  currentStep: string;
}

export const VisionLadder = ({ currentStep }: VisionLadderProps) => {
  const currentIndex = STAGES.findIndex((s) => s.id === currentStep);
  const activeIndex = currentIndex >= 0 ? currentIndex : 0;

  return (
    <div className="w-full min-w-[220px] flex flex-col h-full bg-[#020617] py-8 px-5 workspace-ladder" dir="rtl">
      <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-0">
        {STAGES.map((stage, i) => {
          const isActive = i === activeIndex;
          const isPast = i < activeIndex;
          const isLast = i === STAGES.length - 1;
          return (
            <div key={stage.id} className="flex flex-col items-stretch">
              {/* Rectangle box for each step */}
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
                  {stage.title}
                </div>
                {/* Tooltip on hover */}
                <div
                  className="absolute left-full ml-3 top-1/2 -translate-y-1/2 z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none w-48 p-3 rounded text-[12px]"
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    lineHeight: 1.5,
                    background: 'rgba(2,6,23,0.98)',
                    border: '0.5px solid rgba(255,255,255,0.08)',
                    color: 'rgba(245,245,240,0.9)',
                  }}
                >
                  {stage.tooltip}
                </div>
              </div>
              {/* Connecting line to next step */}
              {!isLast && (
                <div
                  className="w-[1px] flex-shrink-0 mx-auto"
                  style={{
                    height: 8,
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
