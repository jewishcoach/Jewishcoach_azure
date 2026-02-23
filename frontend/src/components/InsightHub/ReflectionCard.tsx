import { motion } from 'framer-motion';
import { Clock, CheckCircle } from 'lucide-react';
import type { ReactNode } from 'react';

interface ReflectionCardProps {
  status: 'draft' | 'final';
  title: string;
  children: ReactNode;
  language?: 'he' | 'en';
}

export const ReflectionCard = ({ status, title, children, language = 'he' }: ReflectionCardProps) => {
  const isDraft = status === 'draft';
  
  const statusConfig = {
    draft: {
      border: 'border-orange-400',
      borderStyle: 'border-dashed',
      bg: 'bg-orange-100/70',
      icon: Clock,
      iconColor: 'text-orange-600',
      badge: language === 'he' ? 'מתגבש' : 'Forming',
      badgeBg: 'bg-orange-200',
      badgeText: 'text-orange-800'
    },
    final: {
      border: 'border-green-500',
      borderStyle: 'border-solid',
      bg: 'bg-green-100/60',
      icon: CheckCircle,
      iconColor: 'text-green-600',
      badge: language === 'he' ? 'נקלט' : 'Saved',
      badgeBg: 'bg-green-200',
      badgeText: 'text-green-800'
    }
  };
  
  const config = statusConfig[status];
  const Icon = config.icon;
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
      className={`
        relative rounded-xl p-4 mb-4
        ${config.bg} ${config.border} ${config.borderStyle} border-2
        transition-all duration-500 ease-in-out
        ${!isDraft && 'shadow-md'}
      `}
    >
      {/* Status Badge */}
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-primary-dark">{title}</h4>
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 300 }}
          className={`
            flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
            ${config.badgeBg} ${config.badgeText}
          `}
        >
          <Icon size={14} className={config.iconColor} />
          <span>{config.badge}</span>
        </motion.div>
      </div>
      
      {/* Content */}
      <motion.div
        initial={{ opacity: 0.7 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        {children}
      </motion.div>
      
      {/* Glow effect on transition to final */}
      {!isDraft && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.3, 0] }}
          transition={{ duration: 1.5 }}
          className="absolute inset-0 rounded-xl bg-green-400 pointer-events-none"
        />
      )}
    </motion.div>
  );
};



