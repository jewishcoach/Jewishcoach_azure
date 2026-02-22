import { motion } from 'framer-motion';

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
    <div className="w-full min-w-[220px] flex flex-col h-full bg-[#020617] py-8 px-5" dir="rtl">
      <div className="flex-1 overflow-y-auto custom-scrollbar relative">
        {/* The Spine - vertical line on the right, 0.5px, Champagne Gold gradient */}
        <div
          className="absolute top-0 bottom-0"
          style={{
            right: 0,
            width: '0.5px',
            minWidth: '0.5px',
            background: 'linear-gradient(to bottom, transparent 0%, #D4AF37 50%, transparent 100%)',
            opacity: 0.8,
          }}
        />
        {/* Active step glow - illuminates the relevant segment of the spine */}
        <div
          className="absolute right-0 transition-all duration-500 ease-out"
          style={{
            top: `${(activeIndex / 13) * 100}%`,
            height: `${100 / 13}%`,
            width: 12,
            background: 'linear-gradient(to left, transparent, rgba(212, 175, 55, 0.12))',
            boxShadow: '0 0 16px rgba(212, 175, 55, 0.2)',
            pointerEvents: 'none',
          }}
        />
        {/* Stage names - aligned left of the spine, generous padding */}
        <div className="relative space-y-0" style={{ paddingRight: 28 }}>
          {STAGES.map((stage, i) => {
            const isActive = i === activeIndex;
            const isPast = i < activeIndex;
            return (
              <motion.div
                key={stage.id}
                className="group relative py-4 pr-2"
                initial={{ opacity: 0.5 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.2 }}
              >
                <div
                  className="text-right transition-all duration-300"
                  style={{
                    fontFamily: 'Cormorant Garamond, Playfair Display, serif',
                    fontWeight: 300,
                    fontSize: 15,
                    letterSpacing: '0.06em',
                    lineHeight: 1.4,
                    color: isActive ? CREAM_WHITE : isPast ? 'rgba(245,245,240,0.55)' : 'rgba(245,245,240,0.3)',
                  }}
                >
                  {stage.title}
                </div>
                {/* Minimal tooltip on hover */}
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
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
