import { motion } from 'framer-motion';
import { Archive } from 'lucide-react';

const STAGES = ['S0', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10', 'S11', 'S12', 'S13'];

interface BsdScaleProps {
  currentStep: string;
  onArchiveClick: () => void;
}

export const BsdScale = ({ currentStep, onArchiveClick }: BsdScaleProps) => {
  const currentIndex = STAGES.indexOf(currentStep);
  const activeIndex = currentIndex >= 0 ? currentIndex : 0;

  return (
    <div className="w-12 flex flex-col items-center h-full bg-[#0F172A] border-r border-white/5">
      {/* Archive button */}
      <motion.button
        onClick={onArchiveClick}
        className="mt-4 p-2 rounded-[4px] text-white/60 hover:text-white hover:bg-white/5 transition-colors"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        aria-label="Archive"
      >
        <Archive size={18} />
      </motion.button>

      {/* Vertical scale */}
      <div className="flex-1 flex flex-col justify-center gap-1 py-6">
        {STAGES.map((stage, i) => {
          const isActive = i === activeIndex;
          const isPast = i < activeIndex;
          return (
            <motion.div
              key={stage}
              className={`
                w-2 h-2 rounded-full transition-colors
                ${isActive ? 'bg-amber-400/90 scale-125' : ''}
                ${isPast ? 'bg-white/40' : ''}
                ${!isActive && !isPast ? 'bg-white/15' : ''}
              `}
              initial={{ opacity: 0.5 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2 }}
            />
          );
        })}
      </div>
    </div>
  );
};
