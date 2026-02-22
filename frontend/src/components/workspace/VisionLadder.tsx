import { motion } from 'framer-motion';

const STAGES: { id: string; title: string; fullLabel: string; tooltip: string }[] = [
  { id: 'S0', title: 'חוזה', fullLabel: 'S0: חוזה', tooltip: 'קבלת רשות להתחיל את תהליך האימון' },
  { id: 'S1', title: 'נושא', fullLabel: 'S1: נושא', tooltip: 'הבנת הנושא הכללי - ללא מצוי/רצוי בשלב זה' },
  { id: 'S2', title: 'אירוע', fullLabel: 'S2: אירוע', tooltip: 'קבלת אירוע ספציפי אחד מפורט (מתי, איפה, מי, מה)' },
  { id: 'S3', title: 'חקירת רגשות', fullLabel: 'S3: חקירת רגשות', tooltip: 'הצפת רגשות ללא שיפוטיות - איסוף 4+ רגשות בעומק' },
  { id: 'S4', title: 'מחשבה', fullLabel: 'S4: מחשבה', tooltip: 'משפט מילולי מדויק שעבר בראש באותו רגע' },
  { id: 'S5', title: 'מצוי ורצוי', fullLabel: 'S5: מצוי ורצוי', tooltip: 'סיכום הדפוס - מה עשה בפועל ומה רצה לעשות' },
  { id: 'S6', title: 'פער', fullLabel: 'S6: פער', tooltip: 'שם וציון לפער בין המצוי לרצוי' },
  { id: 'S7', title: 'זיהוי דפוס', fullLabel: 'S7: זיהוי דפוס', tooltip: 'תגובה החוזרת במצבים שונים - ליבת שיטת BSD' },
  { id: 'S8', title: 'רווחים והפסדים', fullLabel: 'S8: רווחים והפסדים', tooltip: 'מה מרוויח ומה מפסיד מהדפוס' },
  { id: 'S9', title: 'ערכים ויכולות', fullLabel: 'S9: ערכים ויכולות', tooltip: 'ערכים חשובים ויכולות קיימות' },
  { id: 'S10', title: 'בחירה', fullLabel: 'S10: בחירה', tooltip: 'עמדה חדשה שהמשתמש בוחר' },
  { id: 'S11', title: 'חזון', fullLabel: 'S11: חזון', tooltip: 'לאן הבחירה מובילה' },
  { id: 'S12', title: 'מחויבות', fullLabel: 'S12: מחויבות', tooltip: 'פעולה קונקרטית לפעם הבאה' },
];

const CHAMPAGNE_GOLD = '#D4AF37';

interface VisionLadderProps {
  currentStep: string;
}

export const VisionLadder = ({ currentStep }: VisionLadderProps) => {
  const currentIndex = STAGES.findIndex((s) => s.id === currentStep);
  const activeIndex = currentIndex >= 0 ? currentIndex : 0;

  return (
    <div className="w-full min-w-[200px] flex flex-col h-full bg-[#020617] py-5" dir="ltr">
      <h3 className="text-[11px] font-medium text-[#D4AF37]/80 uppercase tracking-[0.2em] px-4 mb-5" style={{ fontFamily: 'Playfair Display, serif' }}>
        סולם התהליך
      </h3>
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 relative">
        {/* Vertical connecting line */}
        <div
          className="absolute top-0 bottom-0 w-px"
          style={{ left: 11, background: `linear-gradient(to bottom, ${CHAMPAGNE_GOLD}40, ${CHAMPAGNE_GOLD}20, transparent)` }}
        />
        <div className="relative space-y-0">
          {STAGES.map((stage, i) => {
            const isActive = i === activeIndex;
            const isPast = i < activeIndex;
            return (
              <motion.div
                key={stage.id}
                className="group relative flex items-start gap-3 py-2"
                initial={{ opacity: 0.5 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.2 }}
              >
                {/* Dot on timeline */}
                <div
                  className="relative z-10 mt-1.5 shrink-0 w-2.5 h-2.5 rounded-full border transition-all duration-200"
                  style={{
                    backgroundColor: isActive ? CHAMPAGNE_GOLD : isPast ? `${CHAMPAGNE_GOLD}60` : 'transparent',
                    borderColor: isActive ? CHAMPAGNE_GOLD : isPast ? `${CHAMPAGNE_GOLD}50` : `${CHAMPAGNE_GOLD}30`,
                    borderWidth: '1px',
                    boxShadow: isActive ? `0 0 8px ${CHAMPAGNE_GOLD}80` : undefined,
                  }}
                />
                {/* Stage label - full text visible */}
                <div
                  className={`
                    flex-1 min-w-0 py-1.5 px-2 rounded-[4px] transition-all duration-200
                    ${isActive
                      ? 'bg-[#D4AF37]/12 border border-[#D4AF37]/40'
                      : isPast
                        ? 'text-white/60'
                        : 'text-white/30'
                    }
                  `}
                  style={{
                    boxShadow: isActive ? `0 0 16px ${CHAMPAGNE_GOLD}25` : undefined,
                    fontFamily: 'Playfair Display, serif',
                    fontSize: 11,
                    textAlign: 'right',
                  }}
                >
                  {stage.fullLabel}
                </div>
                {/* Premium tooltip */}
                <div
                  className="absolute right-full mr-3 top-1/2 -translate-y-1/2 z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none w-52 p-3 rounded-[4px] bg-[#020617]/98 border border-[#D4AF37]/40 text-xs text-white/95 shadow-2xl"
                  style={{ fontFamily: 'Inter, sans-serif', lineHeight: 1.5 }}
                >
                  <div className="text-[#D4AF37]/90 text-[10px] uppercase tracking-wider mb-1" style={{ fontFamily: 'Playfair Display, serif' }}>{stage.fullLabel}</div>
                  {stage.tooltip}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
