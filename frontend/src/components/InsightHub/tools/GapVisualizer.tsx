import { motion } from 'framer-motion';
import { Target, MapPin, ArrowRight } from 'lucide-react';

interface GapVisualizerProps {
  language: 'he' | 'en';
  data?: {
    current_reality: string;
    desired_reality: string;
    gap_insight?: string;
  };
}

export const GapVisualizer = ({ language, data }: GapVisualizerProps) => {
  const isRTL = language === 'he';

  const currentReality = data?.current_reality || (isRTL ? 'המציאות הנוכחית טרם הוגדרה' : 'Current reality not yet defined');
  const desiredReality = data?.desired_reality || (isRTL ? 'המציאות הרצויה טרם הוגדרה' : 'Desired reality not yet defined');
  const gapInsight = data?.gap_insight;

  return (
    <div className="space-y-4">
      {/* Current Reality */}
      <motion.div
        initial={{ x: isRTL ? 50 : -50, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="bg-red-50 border-2 border-red-200 rounded-xl p-4"
      >
        <div className="flex items-start gap-3">
          <MapPin className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-semibold text-red-700 mb-2">
              {isRTL ? 'המצב הנוכחי (המצוי)' : 'Current Reality'}
            </h4>
            <p className="text-sm text-red-900 leading-relaxed" dir={isRTL ? 'rtl' : 'ltr'}>
              {currentReality}
            </p>
          </div>
        </div>
      </motion.div>

      {/* Arrow Indicator */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.3, type: 'spring' }}
        className="flex justify-center py-2"
      >
        <div className="bg-accent/10 p-3 rounded-full">
          <ArrowRight
            className={`w-6 h-6 text-accent ${isRTL ? 'rotate-180' : ''}`}
          />
        </div>
      </motion.div>

      {/* Desired Reality */}
      <motion.div
        initial={{ x: isRTL ? -50 : 50, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="bg-green-50 border-2 border-green-200 rounded-xl p-4"
      >
        <div className="flex items-start gap-3">
          <Target className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-semibold text-green-700 mb-2">
              {isRTL ? 'המצב הרצוי (החזון)' : 'Desired Reality'}
            </h4>
            <p className="text-sm text-green-900 leading-relaxed" dir={isRTL ? 'rtl' : 'ltr'}>
              {desiredReality}
            </p>
          </div>
        </div>
      </motion.div>

      {/* Gap Insight (Optional) */}
      {gapInsight && (
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.7 }}
          className="bg-accent/5 border border-accent/20 rounded-xl p-4"
        >
          <h4 className="font-semibold text-accent mb-2 text-sm">
            {isRTL ? '💡 תובנת הפער' : '💡 Gap Insight'}
          </h4>
          <p className="text-xs text-primary-dark leading-relaxed" dir={isRTL ? 'rtl' : 'ltr'}>
            {gapInsight}
          </p>
        </motion.div>
      )}
    </div>
  );
};




