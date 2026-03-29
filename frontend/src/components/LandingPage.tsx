import { motion } from 'framer-motion';
import { BookOpen, Heart, Layers } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { HEBREW_UI_SANS } from '../constants/workspaceFonts';

interface Props {
  onGetStarted: () => void;
}

const featureIcons = [Heart, BookOpen, Layers] as const;

export const LandingPage = ({ onGetStarted }: Props) => {
  const { t, i18n } = useTranslation();
  const isHe = i18n.language.startsWith('he');

  const features = [
    { titleKey: 'landing.feature1.title', descKey: 'landing.feature1.desc' },
    { titleKey: 'landing.feature2.title', descKey: 'landing.feature2.desc' },
    { titleKey: 'landing.feature3.title', descKey: 'landing.feature3.desc' },
  ] as const;

  return (
    <div
      className="min-h-screen relative flex flex-col items-center justify-center px-4 py-12 sm:py-16 overflow-hidden"
      dir={isHe ? 'rtl' : 'ltr'}
      style={{ fontFamily: HEBREW_UI_SANS }}
    >
      <div className="pointer-events-none absolute inset-0 bg-[#020617]" aria-hidden />
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_85%_55%_at_50%_-10%,rgba(212,162,12,0.12),transparent_58%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_65%_45%_at_100%_100%,rgba(30,41,59,0.45),transparent_52%)]"
        aria-hidden
      />

      <div className="relative z-10 w-full max-w-lg md:max-w-2xl">
        <motion.article
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="
            rounded-2xl border border-white/[0.09] bg-[#0b1220]/75 backdrop-blur-xl
            shadow-[0_24px_48px_-12px_rgba(0,0,0,0.5)]
            px-6 py-10 sm:px-12 sm:py-12
          "
        >
          <div className="text-center">
            <motion.img
              src="/bsd-logo.png"
              alt={t('landing.title')}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.06, duration: 0.4 }}
              className="h-[4.5rem] sm:h-28 object-contain mx-auto mb-7"
            />

            <p className="text-sm sm:text-[0.95rem] text-amber-200/90 font-medium tracking-wide mb-3">
              {t('landing.quote')}
            </p>

            <h1 className="text-[1.35rem] sm:text-2xl md:text-[1.75rem] text-slate-50 font-semibold leading-snug mb-4">
              {t('landing.subtitle')}
            </h1>

            <p className="text-slate-300/95 text-base sm:text-lg leading-relaxed mb-9 max-w-xl mx-auto font-normal">
              {t('landing.heroLead')}
            </p>

            <motion.button
              type="button"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.12, duration: 0.35 }}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              onClick={onGetStarted}
              className="
                w-full sm:w-auto min-h-[52px] px-10 py-3.5 rounded-xl font-semibold text-base
                bg-amber-500 text-stone-950
                shadow-lg shadow-amber-950/30
                hover:bg-amber-400
                focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-300 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0b1220]
                transition-colors duration-200
              "
            >
              {t('landing.primaryCta')}
            </motion.button>

            <p className="mt-4 text-sm text-slate-400 max-w-md mx-auto leading-relaxed">
              {t('landing.ctaHint')}
            </p>
          </div>

          <ul className="mt-11 grid gap-3 sm:grid-cols-3 sm:gap-3 text-start">
            {features.map((feature, index) => {
              const Icon = featureIcons[index];
              return (
                <motion.li
                  key={feature.titleKey}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.28 + index * 0.07, duration: 0.35 }}
                  className="
                    flex gap-3 sm:flex-col sm:text-center sm:items-center
                    rounded-xl border border-white/[0.07] bg-[#020617]/50 px-3.5 py-4 sm:py-4
                    hover:border-white/12 hover:bg-[#020617]/65 transition-colors
                  "
                >
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-amber-500/12 text-amber-200 sm:mx-auto">
                    <Icon className="h-5 w-5" strokeWidth={1.75} aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <h2 className="text-[0.95rem] font-semibold text-slate-100 mb-1 leading-snug">
                      {t(feature.titleKey)}
                    </h2>
                    <p className="text-[0.8125rem] sm:text-sm text-slate-400 leading-relaxed">
                      {t(feature.descKey)}
                    </p>
                  </div>
                </motion.li>
              );
            })}
          </ul>

          <p className="mt-9 text-center text-xs sm:text-[0.8125rem] text-slate-500 leading-relaxed">
            {t('landing.footerNote')}
          </p>
        </motion.article>
      </div>
    </div>
  );
};
