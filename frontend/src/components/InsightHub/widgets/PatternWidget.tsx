import { motion } from 'framer-motion';
import { Zap, RefreshCw, AlertCircle } from 'lucide-react';

interface PatternWidgetProps {
  data: {
    trigger?: string;
    reaction?: string;
    consequence?: string;
  };
  language?: 'he' | 'en';
}

export const PatternWidget = ({ data, language = 'he' }: PatternWidgetProps) => {
  const labels = {
    he: {
      trigger: 'טריגר',
      reaction: 'תגובה',
      consequence: 'תוצאה'
    },
    en: {
      trigger: 'Trigger',
      reaction: 'Reaction',
      consequence: 'Consequence'
    }
  };
  
  const t = labels[language];
  
  const steps = [
    {
      label: t.trigger,
      content: data.trigger,
      icon: Zap,
      color: 'text-yellow-600',
      bg: 'bg-yellow-50',
      border: 'border-yellow-300'
    },
    {
      label: t.reaction,
      content: data.reaction,
      icon: RefreshCw,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      border: 'border-blue-300'
    },
    {
      label: t.consequence,
      content: data.consequence,
      icon: AlertCircle,
      color: 'text-red-600',
      bg: 'bg-red-50',
      border: 'border-red-300'
    }
  ];
  
  return (
    <div className="space-y-2.5">
      {steps.map((step, index) => {
        const Icon = step.icon;
        return (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: language === 'he' ? 20 : -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.15 }}
            className={`
              ${step.bg} border ${step.border} rounded-lg p-3
              flex items-start gap-2.5
            `}
          >
            <div className={`flex-shrink-0 mt-0.5 ${step.color}`}>
              <Icon size={16} />
            </div>
            <div className="flex-1 min-w-0">
              <div className={`text-xs font-semibold ${step.color} mb-1`}>
                {step.label}
              </div>
              <div className="text-sm text-gray-800 leading-relaxed break-words">
                {step.content || (language === 'he' ? 'טרם הוגדר' : 'Not yet defined')}
              </div>
            </div>
          </motion.div>
        );
      })}
      
      {/* Circular Flow Indicator */}
      {data.trigger && data.reaction && data.consequence && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="flex items-center justify-center pt-2"
        >
          <div className="text-xs text-gray-500 italic">
            {language === 'he' ? '↻ דפוס חוזר' : '↻ Recurring Pattern'}
          </div>
        </motion.div>
      )}
    </div>
  );
};




