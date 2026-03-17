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
        animate={{ opacity: 1, height: 4 }}
        exit={{ opacity: 0, height: 0 }}
        className="rounded-b overflow-hidden border-b border-[#2E3A56]/15"
        style={{ background: 'rgba(46, 58, 86, 0.2)' }}
      >
        <motion.div
          className="h-full"
          style={{
            background: 'linear-gradient(90deg, #AA771C, #B38728, #BF953F, #B38728, #8B6914)',
            boxShadow: '0 0 8px rgba(179, 135, 40, 0.4)',
          }}
          initial={{ width: '0%' }}
          animate={{ width: ['0%', '70%', '90%', '100%'] }}
          transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse' }}
        />
      </motion.div>
    </div>
  );
};
