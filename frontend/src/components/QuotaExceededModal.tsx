import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, ArrowLeft } from 'lucide-react';

interface QuotaExceededModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGoToSubscription: () => void;
}

export const QuotaExceededModal = ({ isOpen, onClose, onGoToSubscription }: QuotaExceededModalProps) => {
  const { t, i18n } = useTranslation();
  const isHebrew = i18n.language === 'he' || i18n.language?.startsWith('he');

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="relative w-full max-w-[min(28rem,calc(100vw-2rem))] rounded-2xl overflow-hidden shadow-2xl"
            style={{
              background: 'linear-gradient(165deg, #1e293b 0%, #0f172a 100%)',
              border: '1px solid rgba(255,255,255,0.08)',
              boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Accent line */}
            <div
              className="absolute top-0 left-0 right-0 h-1"
              style={{ background: 'linear-gradient(90deg, #B38728, #FCF6BA, #AA771C)' }}
            />

            <div className="p-8 pt-10" dir={isHebrew ? 'rtl' : 'ltr'}>
              {/* Icon */}
              <div
                className="w-14 h-14 rounded-xl flex items-center justify-center mb-6 mx-auto"
                style={{ background: 'rgba(179, 135, 40, 0.15)' }}
              >
                <Sparkles className="w-7 h-7" style={{ color: '#B38728' }} />
              </div>

              {/* Title */}
              <h2
                className="text-xl font-semibold text-center mb-3"
                style={{ color: '#F5F5F0', fontFamily: 'Heebo, sans-serif' }}
              >
                {isHebrew ? 'הגעת למגבלת ההודעות' : "You've reached your message limit"}
              </h2>

              {/* Description */}
              <p
                className="text-center text-[15px] leading-relaxed mb-8"
                style={{ color: '#94a3b8', fontFamily: 'Inter, sans-serif', lineHeight: 1.65 }}
              >
                {isHebrew
                  ? 'שדרג את המנוי שלך כדי להמשיך את מסע האימון עם גישה מלאה לכל שלבי האימון, יומן אישי ותובנות עומק.'
                  : 'Upgrade your subscription to continue your coaching journey with full access to all stages, personal journal, and deep insights.'}
              </p>

              {/* CTA Button */}
              <button
                onClick={() => {
                  onClose();
                  onGoToSubscription();
                }}
                className="w-full py-4 px-6 rounded-xl font-medium text-[16px] flex items-center justify-center gap-3 transition-all hover:opacity-95 active:scale-[0.98]"
                style={{
                  background: 'linear-gradient(135deg, #B38728 0%, #AA771C 100%)',
                  color: '#fff',
                  fontFamily: 'Heebo, sans-serif',
                  boxShadow: '0 4px 14px rgba(179, 135, 40, 0.35)',
                }}
              >
                {isHebrew ? 'לעמוד המנוי' : 'Go to Subscription'}
                <ArrowLeft
                  className="w-5 h-5"
                  style={{ transform: isHebrew ? 'scaleX(-1)' : 'none' }}
                />
              </button>

              {/* Secondary close */}
              <button
                onClick={onClose}
                className="w-full mt-4 py-2.5 text-sm font-light transition-colors hover:opacity-80"
                style={{ color: '#64748b', fontFamily: 'Inter, sans-serif' }}
              >
                {isHebrew ? 'אמשיך מאוחר יותר' : 'I\'ll continue later'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
