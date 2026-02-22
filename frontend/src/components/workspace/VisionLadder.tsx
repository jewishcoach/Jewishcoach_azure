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

const METALLIC_GOLD = 'linear-gradient(45deg, #BF953F, #FCF6BA, #B38728, #FBF5B7, #AA771C)';
const CREAM_WHITE = '#F5F5F0';

interface VisionLadderProps {
  currentStep: string;
}

export const VisionLadder = ({ currentStep }: VisionLadderProps) => {
  const currentIndex = STAGES.findIndex((s) => s.id === currentStep);
  const activeIndex = currentIndex >= 0 ? currentIndex : 0;

  return (
    <div className="w-full min-w-[240px] flex flex-col h-full bg-[#020617] py-8 px-6" dir="ltr">
      <h3 className="text-[13px] font-light uppercase tracking-[0.1em] mb-8" style={{ fontFamily: 'Cormorant Garamond, Playfair Display, serif', color: CREAM_WHITE, opacity: 0.9 }}>
        סולם התהליך
      </h3>
      <div className="flex-1 overflow-y-auto custom-scrollbar relative">
        {/* Vertical line - metallic gold gradient */}
        <div
          className="absolute top-0 bottom-0 w-[2px] rounded-full"
          style={{
            left: 18,
            background: `linear-gradient(to bottom, #BF953F 0%, #FCF6BA 20%, #B38728 50%, #FBF5B7 80%, #AA771C 100%)`,
            opacity: 0.6,
            filter: 'drop-shadow(0 0 5px rgba(212, 175, 55, 0.5))',
          }}
        />
        <div className="relative space-y-2">
          {STAGES.map((stage, i) => {
            const isActive = i === activeIndex;
            const isPast = i < activeIndex;
            return (
              <motion.div
                key={stage.id}
                className="group relative flex items-start gap-5 py-4"
                initial={{ opacity: 0.5 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.2 }}
              >
                {/* Dot on timeline - metallic when active */}
                <div
                  className="relative z-10 mt-2.5 shrink-0 w-3.5 h-3.5 rounded-full border-2 transition-all duration-300"
                  style={{
                    background: isActive ? METALLIC_GOLD : isPast ? 'rgba(191,149,63,0.5)' : 'transparent',
                    borderColor: isActive ? 'rgba(252,246,186,0.6)' : isPast ? 'rgba(191,149,63,0.4)' : 'rgba(255,255,255,0.15)',
                    filter: isActive ? 'drop-shadow(0 0 8px rgba(212, 175, 55, 0.6))' : undefined,
                    boxShadow: isActive ? '0 0 24px rgba(212,175,55,0.4), 0 0 48px rgba(212,175,55,0.2)' : undefined,
                  }}
                />
                {/* Stage label - cream-white, larger, readable */}
                <div
                  className={`
                    flex-1 min-w-0 py-3 px-4 rounded-[4px] transition-all duration-300
                    ${isActive ? '' : ''}
                  `}
                  style={{
                    background: isActive ? 'rgba(255,255,255,0.04)' : 'transparent',
                    border: isActive ? '0.5px solid rgba(255,255,255,0.12)' : 'none',
                    boxShadow: isActive ? '0 0 32px rgba(212,175,55,0.25), 0 0 64px rgba(212,175,55,0.1), 0 8px 24px rgba(0,0,0,0.4)' : undefined,
                    fontFamily: 'Cormorant Garamond, Playfair Display, serif',
                    fontWeight: 300,
                    fontSize: isActive ? 16 : 14,
                    letterSpacing: '0.1em',
                    textAlign: 'right',
                    color: isActive ? CREAM_WHITE : isPast ? 'rgba(245,245,240,0.65)' : 'rgba(245,245,240,0.4)',
                  }}
                >
                  {stage.fullLabel}
                </div>
                {/* Premium tooltip */}
                <div
                  className="absolute right-full mr-4 top-1/2 -translate-y-1/2 z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none w-60 p-4 rounded-[4px] text-[14px] shadow-2xl"
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    lineHeight: 1.65,
                    background: 'rgba(10,15,26,0.97)',
                    backdropFilter: 'blur(25px)',
                    border: '0.5px solid rgba(255,255,255,0.1)',
                    color: 'rgba(245,245,240,0.95)',
                    boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
                  }}
                >
                  <div className="uppercase tracking-[0.1em] mb-1.5" style={{ fontFamily: 'Cormorant Garamond, serif', color: '#FCF6BA' }}>{stage.fullLabel}</div>
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
