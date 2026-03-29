import { motion } from 'framer-motion';
import { BookOpen, Heart, Layers } from 'lucide-react';
import { useTranslation } from 'react-i18next';

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
      className="min-h-screen relative flex flex-col items-center justify-center px-4 py-14 sm:py-16 overflow-hidden"
      dir={isHe ? 'rtl' : 'ltr'}
    >
      {/* Background layers */}
      <div className="pointer-events-none absolute inset-0 bg-[#020617]" aria-hidden />
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_90%_60%_at_50%_-15%,rgba(191,149,63,0.22),transparent_55%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_100%_100%,rgba(30,41,59,0.55),transparent_50%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_0%_80%,rgba(15,23,42,0.7),transparent_45%)]"
        aria-hidden
      />

      <div className="relative z-10 w-full max-w-lg md:max-w-2xl">
        <motion.article
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
          className="
            rounded-2xl border border-white/[0.1] bg-white/[0.04] backdrop-blur-xl
            shadow-[0_25px_50px_-12px_rgba(0,0,0,0.45),inset_0_1px_0_0_rgba(255,255,255,0.06)]
            px-6 py-10 sm:px-10 sm:py-12
          "
        >
          <div className="text-center">
            <motion.img
              src="/bsd-logo.png"
              alt={t('landing.title')}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.08, duration: 0.45 }}
              className="h-20 sm:h-24 object-contain mx-auto mb-6"
            />

            <p
              className="text-sm sm:text-base text-[#FCF6BA]/90 font-medium tracking-wide mb-2"
              style={{ fontFamily: 'Cormorant Garamond, Georgia, serif' }}
            >
              {t('landing.quote')}
            </p>

            <h1
              className="text-lg sm:text-xl text-[#f5f5f0]/95 font-semibold mb-2"
              style={{ fontFamily: 'Inter, system-ui, sans-serif' }}
            >
              {t('landing.subtitle')}
            </h1>

            <p className="text-[#f5f5f0]/75 text-sm sm:text-base leading-relaxed mb-8 max-w-md mx-auto">
              {t('landing.heroLead')}
            </p>

            <motion.button
              type="button"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.4 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={onGetStarted}
              className="
                w-full sm:w-auto min-h-[52px] px-8 py-3.5 rounded-xl font-semibold text-base
                bg-gradient-to-r from-[#BF953F] via-[#FCF6BA] to-[#B38728] text-[#020617]
                shadow-[0_8px_24px_-4px_rgba(191,149,63,0.45)]
                hover:brightness-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#FCF6BA] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f172a]
                transition-[transform,filter] duration-200
              "
            >
              {t('landing.primaryCta')}
            </motion.button>

            <p className="mt-3 text-xs sm:text-sm text-[#f5f5f0]/50">{t('landing.ctaHint')}</p>
          </div>

          <ul className="mt-10 grid gap-3 sm:grid-cols-3 sm:gap-2 text-start">
            {features.map((feature, index) => {
              const Icon = featureIcons[index];
              return (
                <motion.li
                  key={feature.titleKey}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.35 + index * 0.08, duration: 0.4 }}
                  className="
                    flex gap-3 sm:flex-col sm:text-center sm:items-center
                    rounded-xl border border-white/[0.08] bg-[#020617]/40 px-3 py-3 sm:py-4
                    hover:border-white/[0.14] hover:bg-[#020617]/60 transition-colors
                  "
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#FCF6BA]/12 text-[#FCF6BA] sm:mx-auto">
                    <Icon className="h-5 w-5" strokeWidth={1.75} aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <h2 className="text-sm font-semibold text-[#f5f5f0] mb-0.5 leading-snug">
                      {t(feature.titleKey)}
                    </h2>
                    <p className="text-xs text-[#f5f5f0]/65 leading-relaxed">{t(feature.descKey)}</p>
                  </div>
                </motion.li>
              );
            })}
          </ul>

          <p className="mt-8 text-center text-[11px] sm:text-xs text-[#f5f5f0]/40 tracking-wide">
            {t('landing.footerNote')}
          </p>
        </motion.article>
      </div>
    </div>
  );
};
