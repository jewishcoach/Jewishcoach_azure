import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

interface GapWidgetProps {
  data: {
    current_reality?: string;
    desired_reality?: string;
  };
  language?: 'he' | 'en';
}

export const GapWidget = ({ data, language = 'he' }: GapWidgetProps) => {
  const labels = {
    he: {
      current: 'המצב הנוכחי',
      desired: 'המצב הרצוי',
      gap: 'הפער = ההזדמנות'
    },
    en: {
      current: 'Current Reality',
      desired: 'Desired Reality',
      gap: 'Gap = Opportunity'
    }
  };
  
  const t = labels[language];
  
  return (
    <div className="space-y-3">
      {/* Current Reality */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-3">
        <div className="text-xs font-semibold text-red-700 mb-1">{t.current}</div>
        <div className="text-sm text-gray-800 leading-relaxed">
          {data.current_reality || (language === 'he' ? 'טרם הוגדר' : 'Not yet defined')}
        </div>
      </div>
      
      {/* Arrow with Gap Label */}
      <div className="flex items-center justify-center gap-2 py-1">
        <motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="flex items-center gap-2 text-purple-600"
        >
          <ArrowRight size={20} className="rtl:rotate-180" />
          <span className="text-xs font-semibold">{t.gap}</span>
        </motion.div>
      </div>
      
      {/* Desired Reality */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-3">
        <div className="text-xs font-semibold text-green-700 mb-1">{t.desired}</div>
        <div className="text-sm text-gray-800 leading-relaxed">
          {data.desired_reality || (language === 'he' ? 'טרם הוגדר' : 'Not yet defined')}
        </div>
      </div>
    </div>
  );
};




