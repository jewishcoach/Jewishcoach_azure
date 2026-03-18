import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Props {
  onGetStarted: () => void;
}

export const LandingPage = ({ onGetStarted }: Props) => {
  const { i18n } = useTranslation();

  const features = [
    {
      titleHe: 'אימון אמפתי',
      titleEn: 'Empathetic Coaching',
      descHe: 'מאמן שמקשיב, מבין, ומוביל עם חום ואכפתיות',
      descEn: 'A coach that listens, understands, and leads with warmth',
    },
    {
      titleHe: 'מתודולוגיה יהודית',
      titleEn: 'Jewish Methodology',
      descHe: 'מבוסס על עקרונות עמוקים של חכמת היהדות',
      descEn: 'Based on deep principles of Jewish wisdom',
    },
    {
      titleHe: 'התקדמות מובנית',
      titleEn: 'Structured Progress',
      descHe: 'מעבר שיטתי דרך 11 שלבי גילוי עצמי',
      descEn: 'Systematic journey through 11 phases of self-discovery',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary via-primary-light to-primary-dark flex items-center justify-center p-4">
      <div className="max-w-4xl w-full">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-12"
        >
          {/* Logo / Icon */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-accent-light to-accent rounded-full shadow-glow mb-6"
          >
            <Sparkles className="w-10 h-10 text-white" />
          </motion.div>

          {/* Title */}
          <motion.img
            src="/bsd-logo.png"
            alt="BSD אימון יהודי - פשטות. הנאה. תוצאות."
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="h-24 md:h-28 mb-4 object-contain mx-auto"
          />

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="text-xl md:text-2xl text-blue-100 mb-8 max-w-2xl mx-auto leading-relaxed"
          >
            {i18n.language === 'he'
              ? 'מסע אישי של גילוי עצמי, צמיחה, ומימוש הפוטנציאל שלך'
              : 'A personal journey of self-discovery, growth, and realizing your potential'}
          </motion.p>

          {/* CTA Button */}
          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
            whileHover={{ scale: 1.05, boxShadow: '0 0 30px rgba(245, 158, 11, 0.5)' }}
            whileTap={{ scale: 0.95 }}
            onClick={onGetStarted}
            className="
              px-8 py-4 bg-gradient-to-r from-accent to-accent-dark
              text-white font-bold text-lg rounded-xl
              shadow-glow hover:shadow-xl
              transition-all duration-300
            "
          >
            {i18n.language === 'he' ? 'התחל את המסע 🚀' : 'Start Your Journey 🚀'}
          </motion.button>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="grid md:grid-cols-3 gap-4 mt-12"
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1 + index * 0.2 }}
              whileHover={{ y: -3 }}
              className="
                bg-white/10 backdrop-blur-md rounded-xl px-4 py-3
                border border-white/20 shadow-glass
                hover:bg-white/20 transition-all duration-300
              "
            >
              <h3 className="text-base font-serif font-bold text-white mb-1">
                {i18n.language === 'he' ? feature.titleHe : feature.titleEn}
              </h3>
              <p className="text-blue-100 text-sm leading-relaxed">
                {i18n.language === 'he' ? feature.descHe : feature.descEn}
              </p>
            </motion.div>
          ))}
        </motion.div>

      </div>
    </div>
  );
};
