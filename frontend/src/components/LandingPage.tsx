import { motion } from 'framer-motion';
import { Sparkles, Heart, Brain, Target } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Props {
  onGetStarted: () => void;
}

export const LandingPage = ({ onGetStarted }: Props) => {
  const { i18n } = useTranslation();

  const features = [
    {
      icon: Heart,
      titleHe: 'אימון אמפתי',
      titleEn: 'Empathetic Coaching',
      descHe: 'מאמן שמקשיב, מבין, ומוביל עם חום ואכפתיות',
      descEn: 'A coach that listens, understands, and leads with warmth',
    },
    {
      icon: Brain,
      titleHe: 'מתודולוגיה יהודית',
      titleEn: 'Jewish Methodology',
      descHe: 'מבוסס על עקרונות עמוקים של חכמת היהדות',
      descEn: 'Based on deep principles of Jewish wisdom',
    },
    {
      icon: Target,
      titleHe: 'התקדמות מובנית',
      titleEn: 'Structured Progress',
      descHe: 'מעבר שיטתי דרך 9 שלבי גילוי עצמי',
      descEn: 'Systematic journey through 9 phases of self-discovery',
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
          <motion.h1
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-5xl md:text-6xl font-serif font-bold text-white mb-4"
          >
            {i18n.language === 'he' ? 'המאמן היהודי' : 'Jewish Coach AI'}
          </motion.h1>

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
          className="grid md:grid-cols-3 gap-6 mt-16"
        >
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1 + index * 0.2 }}
                whileHover={{ y: -5 }}
                className="
                  bg-white/10 backdrop-blur-md rounded-2xl p-6
                  border border-white/20 shadow-glass
                  hover:bg-white/20 transition-all duration-300
                "
              >
                <div className="flex items-center justify-center w-12 h-12 bg-accent/20 rounded-xl mb-4">
                  <Icon className="w-6 h-6 text-accent" />
                </div>
                <h3 className="text-xl font-serif font-bold text-white mb-2">
                  {i18n.language === 'he' ? feature.titleHe : feature.titleEn}
                </h3>
                <p className="text-blue-100">
                  {i18n.language === 'he' ? feature.descHe : feature.descEn}
                </p>
              </motion.div>
            );
          })}
        </motion.div>

        {/* Footer Quote */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.8 }}
          className="text-center mt-16"
        >
          <p className="text-blue-200 italic text-lg">
            {i18n.language === 'he'
              ? '"גלה את המקור שלך, בחר את הדרך החדשה"'
              : '"Discover your Source, Choose your new path"'}
          </p>
          <p className="text-blue-300 text-sm mt-2">בס״ד</p>
        </motion.div>
      </div>
    </div>
  );
};
