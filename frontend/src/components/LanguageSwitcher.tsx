import { useTranslation } from 'react-i18next';
import { Languages } from 'lucide-react';
import { motion } from 'framer-motion';

type LanguageSwitcherProps = {
  /** Dark chrome for workspace header (Figma TOPBAR). */
  variant?: 'light' | 'dark';
};

export const LanguageSwitcher = ({ variant = 'light' }: LanguageSwitcherProps) => {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'he' ? 'en' : 'he';
    void i18n.changeLanguage(newLang);
  };

  if (variant === 'dark') {
    const isHe = i18n.language.startsWith('he');
    return (
      <div
        className="flex h-[31px] w-[80px] shrink-0 overflow-hidden rounded-[8px] border border-[#3a404e] bg-[#1c2333]"
        role="group"
        aria-label={i18n.t('language.switch')}
      >
        <button
          type="button"
          onClick={() => void i18n.changeLanguage('he')}
          className={`flex flex-1 items-center justify-center text-[12px] font-bold transition-colors ${
            isHe ? 'bg-[#c9963a] text-[#1c2535]' : 'text-[rgba(255,255,255,0.55)] hover:text-white/80'
          }`}
        >
          עב
        </button>
        <button
          type="button"
          onClick={() => void i18n.changeLanguage('en')}
          className={`flex flex-1 items-center justify-center text-[12px] font-bold transition-colors ${
            !isHe ? 'bg-[#c9963a] text-[#1c2535]' : 'text-[rgba(255,255,255,0.55)] hover:text-white/80'
          }`}
        >
          EN
        </button>
      </div>
    );
  }

  return (
    <motion.button
      type="button"
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
        {i18n.language.startsWith('he') ? 'EN' : 'עב'}
      </span>
    </motion.button>
  );
};
