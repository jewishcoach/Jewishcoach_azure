import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const SHEHIYA_PHRASES = [
  'מזהה רגשות...',
  'בונה תמונת מצב...',
  'משהה למחשבה...',
  'מקשיב...',
  'מעבד...',
];

interface ShehiyaProgressProps {
  loading: boolean;
  phraseIndex?: number;
}

export const ShehiyaProgress = ({ loading }: ShehiyaProgressProps) => {
  const [phraseIndex, setPhraseIndex] = useState(0);

  useEffect(() => {
    if (!loading) return;
    const t = setInterval(() => setPhraseIndex((i) => (i + 1) % SHEHIYA_PHRASES.length), 2500);
    return () => clearInterval(t);
  }, [loading]);

  if (!loading) return null;

  const phrase = SHEHIYA_PHRASES[phraseIndex];

  return (
    <div className="absolute top-0 left-0 right-0 z-10">
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 2 }}
        exit={{ opacity: 0, height: 0 }}
        className="rounded-b overflow-hidden"
        style={{ background: 'rgba(255,255,255,0.06)' }}
      >
        <motion.div
          className="h-full"
          style={{ background: 'linear-gradient(90deg, #BF953F, #FCF6BA, #B38728, #FBF5B7, #AA771C)' }}
          initial={{ width: '0%' }}
          animate={{ width: ['0%', '70%', '90%', '100%'] }}
          transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse' }}
        />
      </motion.div>
      <div className="absolute top-2 left-6 text-[13px] font-light tracking-[0.05em]" style={{ fontFamily: 'Cormorant Garamond, serif', color: '#FCF6BA' }}>
        {phrase}
      </div>
    </div>
  );
};
