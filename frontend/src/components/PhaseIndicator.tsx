import { motion, AnimatePresence } from 'framer-motion';
import { Check, Circle } from 'lucide-react';
import { useState } from 'react';

interface Phase {
  id: string;
  nameHe: string;
  nameEn: string;
  descriptionHe: string;
  descriptionEn: string;
}

// Map backend stages (S0-S12) to UI display phases
// Multiple backend stages can map to the same UI phase
const PHASE_MAPPING: Record<string, number> = {
  'S0': 0,  // רשות
  'S1': 1, 'S2': 1, 'S3': 1, 'S4': 1,  // המצוי (topic, event, emotions, thought, action-actual)
  'S5': 2,  // רצוי (action-desired, emotion-desired, thought-desired)
  'S6': 3,  // הפער
  'S7': 4,  // דפוס ופרדיגמה
  'S8': 5,  // עמדה/רצון
  'S9': 6,  // כמ"ז
  'S10': 7, 'S11': 7, 'S12': 7, // בחירה חדשה ומחויבות
};

const PHASES: Phase[] = [
  { 
    id: 'contract', 
    nameHe: 'רשות', 
    nameEn: 'Permission',
    descriptionHe: 'קבלת רשות להתחיל את האימון',
    descriptionEn: 'Getting permission to start coaching'
  },
  { 
    id: 'situation', 
    nameHe: 'המצוי', 
    nameEn: 'Actual',
    descriptionHe: 'תיאור המצב הנוכחי - אירוע, רגשות, מחשבות ופעולה',
    descriptionEn: 'Current situation - event, emotions, thoughts and action'
  },
  { 
    id: 'desired', 
    nameHe: 'רצוי', 
    nameEn: 'Desired',
    descriptionHe: 'איך היית רוצה - פעולה, רגש ומחשבה רצויים',
    descriptionEn: 'How you want it - desired action, emotion and thought'
  },
  { 
    id: 'gap', 
    nameHe: 'הפער', 
    nameEn: 'Gap',
    descriptionHe: 'זיהוי הפער בין המצוי לרצוי',
    descriptionEn: 'Identifying the gap between actual and desired'
  },
  { 
    id: 'pattern', 
    nameHe: 'הדפוס', 
    nameEn: 'Pattern',
    descriptionHe: 'גילוי הדפוסים והאמונות החוזרים',
    descriptionEn: 'Discovering recurring patterns and beliefs'
  },
  { 
    id: 'stance', 
    nameHe: 'עמדה', 
    nameEn: 'Stance',
    descriptionHe: 'הבנת העמדה הפנימית והרצון להיות',
    descriptionEn: 'Understanding inner stance and desire to be'
  },
  { 
    id: 'kmz', 
    nameHe: 'כמ"ז', 
    nameEn: 'KMZ',
    descriptionHe: 'כוח, מקור, זהות - חיבור לכוח הפנימי',
    descriptionEn: 'Strength, Source, Identity - connecting to inner power'
  },
  { 
    id: 'new_choice', 
    nameHe: 'בחירה חדשה', 
    nameEn: 'New Choice',
    descriptionHe: 'קבלת החלטה על הבחירה והמחויבות החדשה',
    descriptionEn: 'Making a decision about new choice and commitment'
  },
];

interface Props {
  currentPhase: string;
  language: string;
}

export const PhaseIndicator = ({ currentPhase, language }: Props) => {
  // Map backend stage (S0-S10) to display phase index (0-5)
  const currentIndex = PHASE_MAPPING[currentPhase] ?? 0;
  const [hoveredPhase, setHoveredPhase] = useState<number | null>(null);
  
  return (
    <div className="w-full bg-white/80 backdrop-blur-md shadow-glass rounded-2xl p-6 mb-6">
      {/* Title */}
      <div className="text-center mb-6">
        <h2 className="text-lg font-serif font-bold text-primary">
          {language === 'he' ? 'מסע האימון שלך' : 'Your Coaching Journey'}
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          {language === 'he' 
            ? `שלב ${currentIndex + 1} מתוך ${PHASES.length}` 
            : `Phase ${currentIndex + 1} of ${PHASES.length}`}
        </p>
      </div>

      {/* Progress Bar */}
      <div className="relative">
        {/* Background Line */}
        <div className="absolute top-5 start-0 end-0 h-0.5 bg-gray-200" 
             style={{ 
               marginInlineStart: '1.25rem', 
               marginInlineEnd: '1.25rem' 
             }} 
        />
        
        {/* Progress Line */}
        <motion.div
          className="absolute top-5 start-0 h-0.5 bg-gradient-to-r from-accent to-accent-dark"
          initial={{ width: 0 }}
          animate={{ 
            width: `${(currentIndex / (PHASES.length - 1)) * 100}%`,
            marginInlineStart: '1.25rem'
          }}
          transition={{ duration: 0.8, ease: 'easeInOut' }}
        />

        {/* Phase Circles */}
        <div className="relative flex justify-between">
          {PHASES.map((phase, index) => {
            const isCompleted = index < currentIndex;
            const isCurrent = index === currentIndex;
            const isFuture = index > currentIndex;

            return (
              <motion.div
                key={phase.id}
                className="flex flex-col items-center relative"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: index * 0.1 }}
                onMouseEnter={() => setHoveredPhase(index)}
                onMouseLeave={() => setHoveredPhase(null)}
              >
                {/* Circle */}
                <motion.div
                  className={`
                    relative z-10 flex items-center justify-center rounded-full cursor-pointer
                    ${isCurrent ? 'w-10 h-10 bg-accent shadow-glow' : ''}
                    ${isCompleted ? 'w-8 h-8 bg-primary' : ''}
                    ${isFuture ? 'w-6 h-6 bg-gray-300' : ''}
                    transition-all duration-300
                  `}
                  whileHover={{ scale: 1.1 }}
                >
                  {isCompleted && <Check className="w-4 h-4 text-white" />}
                  {isCurrent && <Circle className="w-5 h-5 text-white fill-current" />}
                  {isFuture && <div className="w-2 h-2 bg-gray-400 rounded-full" />}
                </motion.div>

                {/* Phase Name */}
                <motion.span
                  className={`
                    mt-2 text-xs font-medium text-center whitespace-nowrap
                    ${isCurrent ? 'text-accent font-bold' : ''}
                    ${isCompleted ? 'text-primary' : ''}
                    ${isFuture ? 'text-gray-400' : ''}
                  `}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 + 0.2 }}
                >
                  {language === 'he' ? phase.nameHe : phase.nameEn}
                </motion.span>

                {/* Tooltip */}
                <AnimatePresence>
                  {hoveredPhase === index && (
                    <motion.div
                      className="absolute bottom-full mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-xl z-50 whitespace-nowrap pointer-events-none"
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 5 }}
                      transition={{ duration: 0.2 }}
                      style={{
                        direction: language === 'he' ? 'rtl' : 'ltr'
                      }}
                    >
                      {language === 'he' ? phase.descriptionHe : phase.descriptionEn}
                      {/* Arrow */}
                      <div className="absolute top-full start-1/2 -translate-x-1/2 -mt-1">
                        <div className="w-2 h-2 bg-gray-900 rotate-45"></div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Current Phase Description */}
      <motion.div
        className="mt-6 text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-accent/10 rounded-full border border-accent/30">
          <Circle className="w-4 h-4 text-accent fill-current" />
          <span className="text-sm font-medium text-primary">
            {language === 'he' ? 'שלב נוכחי: ' : 'Current Phase: '}
            <span className="text-accent font-bold">
              {language === 'he' 
                ? PHASES[currentIndex]?.nameHe 
                : PHASES[currentIndex]?.nameEn}
            </span>
          </span>
        </div>
      </motion.div>
    </div>
  );
};




