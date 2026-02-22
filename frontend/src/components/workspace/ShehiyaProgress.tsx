import { motion } from 'framer-motion';

interface ShehiyaProgressProps {
  loading: boolean;
}

export const ShehiyaProgress = ({ loading }: ShehiyaProgressProps) => {
  if (!loading) return null;

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
          style={{
            background: 'linear-gradient(90deg, #BF953F, #FCF6BA, #B38728, #FBF5B7, #AA771C)',
            filter: 'drop-shadow(0 0 5px rgba(212, 175, 55, 0.5))',
          }}
          initial={{ width: '0%' }}
          animate={{ width: ['0%', '70%', '90%', '100%'] }}
          transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse' }}
        />
      </motion.div>
    </div>
  );
};
