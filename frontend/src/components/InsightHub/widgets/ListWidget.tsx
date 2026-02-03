import { motion } from 'framer-motion';
import { Circle, Plus, Minus } from 'lucide-react';

interface ListWidgetProps {
  data: {
    pain_points?: string[];
    gains?: string[];
    losses?: string[];
    limiting_belief?: string;
  };
  stage: string; // 'Situation', 'Stance', 'Paradigm'
  language?: 'he' | 'en';
}

export const ListWidget = ({ data, stage, language = 'he' }: ListWidgetProps) => {
  const labels = {
    he: {
      pain_points: 'נקודות כאב',
      gains: 'מה מרוויח',
      losses: 'מה מפסיד',
      limiting_belief: 'אמונה מגבילה',
      empty: 'טרם הוגדר'
    },
    en: {
      pain_points: 'Pain Points',
      gains: 'Gains',
      losses: 'Losses',
      limiting_belief: 'Limiting Belief',
      empty: 'Not yet defined'
    }
  };
  
  const t = labels[language];
  
  // Render based on stage
  if (stage === 'Situation' && data.pain_points) {
    return (
      <div>
        <div className="text-xs font-semibold text-gray-600 mb-2">{t.pain_points}</div>
        <div className="space-y-1.5">
          {data.pain_points.length > 0 ? (
            data.pain_points.map((point, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: language === 'he' ? 20 : -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-start gap-2 text-sm text-gray-800 bg-white/60 rounded-lg p-2.5 border border-gray-200"
              >
                <Circle size={12} className="text-orange-500 flex-shrink-0 mt-1" fill="currentColor" />
                <span className="flex-1 leading-relaxed">{point}</span>
              </motion.div>
            ))
          ) : (
            <div className="text-sm text-gray-500 italic text-center py-3">{t.empty}</div>
          )}
        </div>
      </div>
    );
  }
  
  if (stage === 'Stance' && (data.gains || data.losses)) {
    return (
      <div className="space-y-4">
        {/* Gains */}
        {data.gains && (
          <div>
            <div className="text-xs font-semibold text-green-700 mb-2">{t.gains}</div>
            <div className="space-y-1.5">
              {data.gains.length > 0 ? (
                data.gains.map((gain, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: language === 'he' ? 20 : -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-start gap-2 text-sm text-gray-800 bg-green-50 rounded-lg p-2.5 border border-green-200"
                  >
                    <Plus size={14} className="text-green-600 flex-shrink-0 mt-0.5" />
                    <span className="flex-1 leading-relaxed">{gain}</span>
                  </motion.div>
                ))
              ) : (
                <div className="text-sm text-gray-500 italic text-center py-2">{t.empty}</div>
              )}
            </div>
          </div>
        )}
        
        {/* Losses */}
        {data.losses && (
          <div>
            <div className="text-xs font-semibold text-red-700 mb-2">{t.losses}</div>
            <div className="space-y-1.5">
              {data.losses.length > 0 ? (
                data.losses.map((loss, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: language === 'he' ? 20 : -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 + 0.3 }}
                    className="flex items-start gap-2 text-sm text-gray-800 bg-red-50 rounded-lg p-2.5 border border-red-200"
                  >
                    <Minus size={14} className="text-red-600 flex-shrink-0 mt-0.5" />
                    <span className="flex-1 leading-relaxed">{loss}</span>
                  </motion.div>
                ))
              ) : (
                <div className="text-sm text-gray-500 italic text-center py-2">{t.empty}</div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }
  
  if (stage === 'Paradigm' && data.limiting_belief) {
    return (
      <div>
        <div className="text-xs font-semibold text-purple-700 mb-2">{t.limiting_belief}</div>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-purple-50 border border-purple-200 rounded-lg p-3 text-sm text-gray-800 leading-relaxed"
        >
          {data.limiting_belief || t.empty}
        </motion.div>
      </div>
    );
  }
  
  // Fallback
  return (
    <div className="text-sm text-gray-500 italic text-center py-4">
      {t.empty}
    </div>
  );
};




