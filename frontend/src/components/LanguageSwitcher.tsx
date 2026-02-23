import { useTranslation } from 'react-i18next';
import { Languages } from 'lucide-react';
import { motion } from 'framer-motion';

export const LanguageSwitcher = () => {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'he' ? 'en' : 'he';
    i18n.changeLanguage(newLang);
  };

  return (
    <motion.button
      onClick={toggleLanguage}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className="
        flex items-center gap-2 px-4 py-2 rounded-xl
        bg-white/[0.06] backdrop-blur-sm border border-white/[0.08]
        hover:bg-white/[0.1] hover:shadow-md
        transition-all duration-200
      "
      aria-label={i18n.t('language.switch')}
    >
      <Languages size={18} className="text-[#FCF6BA]" />
      <span className="font-medium text-[#F5F5F0]">
        {i18n.language === 'he' ? 'EN' : 'עב'}
      </span>
    </motion.button>
  );
};

