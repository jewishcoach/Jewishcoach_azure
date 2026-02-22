import { motion } from 'framer-motion';

const SHEHIYA_PHRASES = [
  'מזהה רגשות...',
  'בונה תמונת מצב...',
  'מקשיב...',
  'מעבד...',
];

interface ShehiyaProgressProps {
  loading: boolean;
  phraseIndex?: number;
}

export const ShehiyaProgress = ({ loading, phraseIndex = 0 }: ShehiyaProgressProps) => {
  if (!loading) return null;

  const phrase = SHEHIYA_PHRASES[phraseIndex % SHEHIYA_PHRASES.length];

  return (
    <div className="absolute top-0 left-0 right-0 z-10">
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 3 }}
        exit={{ opacity: 0, height: 0 }}
        className="bg-amber-500/80 rounded-b overflow-hidden"
      >
        <motion.div
          className="h-full bg-amber-400"
          initial={{ width: '0%' }}
          animate={{ width: ['0%', '70%', '90%', '100%'] }}
          transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse' }}
        />
      </motion.div>
      <div className="absolute top-1 left-4 text-xs text-amber-400/90 font-medium">
        {phrase}
      </div>
    </div>
  );
};
