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
        flex items-center gap-2 px-3 md:px-4 py-2 rounded-xl min-h-[44px]
        bg-white border border-[#E2E4E8] text-[#2E3A56] shadow-sm
        hover:bg-[#F4F6F9] hover:border-[#CCD6E0] active:bg-[#EEF1F4]
        transition-all duration-200
      "
      aria-label={i18n.t('language.switch')}
    >
      <Languages size={18} className="text-[#2E3A56] flex-shrink-0" strokeWidth={2} />
      <span className="font-medium text-[#2E3A56] text-xs md:text-sm">
        {i18n.language === 'he' ? 'EN' : 'עב'}
      </span>
    </motion.button>
  );
};

