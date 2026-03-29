import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { UserButton } from '@clerk/clerk-react';
import { Sparkles, MessageCircle, BookOpen, User, ChevronRight, ExternalLink } from 'lucide-react';
import { LanguageSwitcher } from './LanguageSwitcher';
import { setOnboardingComplete } from '../lib/onboardingStorage';
import { HEBREW_UI_SANS } from '../constants/workspaceFonts';
import beniGalImg from '../assets/beni-gal.png';

interface OnboardingFlowProps {
  onComplete: () => void;
}

const BSD_COACH_URL = 'https://bsdcoach.com';

export function OnboardingFlow({ onComplete }: OnboardingFlowProps) {
  const { t, i18n } = useTranslation();
  const [step, setStep] = useState(0);
  const isHe = i18n.language.startsWith('he');

  const handleComplete = () => {
    setOnboardingComplete();
    onComplete();
  };

  const screens = [
    {
      icon: User,
      titleKey: 'onboarding.founder.title',
      descKey: 'onboarding.founder.desc',
      ctaKey: 'onboarding.next',
      linkKey: 'onboarding.learnMore',
      image: beniGalImg,
    },
    {
      icon: Sparkles,
      titleKey: 'onboarding.welcome.title',
      descKey: 'onboarding.welcome.desc',
      ctaKey: 'onboarding.next',
    },
    {
      icon: MessageCircle,
      titleKey: 'onboarding.coach.title',
      descKey: 'onboarding.coach.desc',
      ctaKey: 'onboarding.next',
      linkKey: 'onboarding.learnMore',
    },
    {
      icon: BookOpen,
      titleKey: 'onboarding.method.title',
      descKey: 'onboarding.method.desc',
      ctaKey: 'onboarding.next',
      linkKey: 'onboarding.learnMore',
    },
    {
      icon: Sparkles,
      titleKey: 'onboarding.ready.title',
      descKey: 'onboarding.ready.desc',
      ctaKey: 'onboarding.start',
    },
  ];

  const currentScreen = screens[step];
  const Icon = currentScreen.icon;
  const isLast = step === screens.length - 1;

  return (
    <div
      className="min-h-screen flex flex-col relative overflow-hidden"
      dir={isHe ? 'rtl' : 'ltr'}
      style={{ fontFamily: HEBREW_UI_SANS, background: '#020617' }}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(148,163,184,0.07),transparent_55%)]" aria-hidden />
      <div className="flex justify-end items-center gap-3 p-4 absolute top-0 end-0 z-10">
        <LanguageSwitcher />
        <UserButton afterSignOutUrl="/" />
      </div>
      <div className="flex-1 flex flex-col items-center justify-center p-6 relative z-[1]">
        <div className="max-w-xl w-full">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: isHe ? 16 : -16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: isHe ? -16 : 16 }}
              transition={{ duration: 0.25 }}
              className="text-center"
            >
              {currentScreen.image ? (
                <div className="flex justify-center mb-8">
                  <div
                    className="
                      inline-flex rounded-full p-[5px]
                      bg-gradient-to-br from-white/45 via-[#FCF6BA]/35 to-[#B38728]/45
                      shadow-[0_12px_40px_-6px_rgba(0,0,0,0.65),0_0_52px_-10px_rgba(252,246,186,0.24),inset_0_1px_0_rgba(255,255,255,0.2)]
                    "
                  >
                    <img
                      src={currentScreen.image}
                      alt=""
                      className="w-40 h-40 md:w-48 md:h-48 rounded-full object-cover block ring-[3px] ring-[#020617]/95"
                    />
                  </div>
                </div>
              ) : (
                <div className="flex justify-center mb-8" aria-hidden>
                  <Icon
                    className="w-11 h-11 md:w-12 md:h-12 text-[#FCF6BA]/88 drop-shadow-[0_0_32px_rgba(252,246,186,0.38),0_0_14px_rgba(255,255,255,0.07)]"
                    strokeWidth={1.35}
                  />
                </div>
              )}
              <h1 className="text-2xl md:text-[1.75rem] font-semibold text-[#FCF6BA] mb-5 leading-snug tracking-tight drop-shadow-[0_0_24px_rgba(252,246,186,0.12)]">
                {t(currentScreen.titleKey)}
              </h1>
              <p className="text-slate-300 text-lg md:text-xl leading-relaxed mb-8 max-w-md mx-auto font-normal">
                {t(currentScreen.descKey)}
              </p>

              {currentScreen.linkKey && (
                <a
                  href={BSD_COACH_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-slate-300 hover:text-white text-sm font-medium mb-8 transition-colors"
                >
                  <ExternalLink className="w-4 h-4 shrink-0" />
                  {t(currentScreen.linkKey)}
                </a>
              )}

              <div
                className={
                  step > 0
                    ? 'grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-xl mx-auto items-stretch'
                    : 'flex w-full max-w-xl mx-auto justify-center'
                }
              >
                {step > 0 && (
                  <button
                    type="button"
                    onClick={() => setStep(step - 1)}
                    className="min-h-[52px] w-full px-8 sm:px-10 py-3.5 rounded-full bg-white/10 text-slate-100 hover:bg-white/14 transition-colors text-base font-medium border border-white/10 inline-flex items-center justify-center"
                  >
                    {t('onboarding.back')}
                  </button>
                )}
                <button
                  type="button"
                  onClick={isLast ? handleComplete : () => setStep(step + 1)}
                  className={`premium-cta-btn inline-flex items-center justify-center gap-2 min-h-[52px] w-full px-8 sm:px-12 py-3.5 rounded-full text-base ${
                    step === 0 ? 'max-w-md sm:max-w-lg' : ''
                  }`}
                >
                  {t(currentScreen.ctaKey)}
                  <ChevronRight className={`w-5 h-5 shrink-0 ${isHe ? 'rotate-180' : ''}`} />
                </button>
              </div>
            </motion.div>
          </AnimatePresence>

          <div className="flex justify-center gap-2 mt-14">
            {screens.map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setStep(i)}
                className={`h-2 rounded-full transition-all duration-300 ${
                  i === step
                    ? 'w-8 bg-gradient-to-r from-[#fafaf8] to-[#e8e5df] shadow-[0_0_12px_rgba(250,250,248,0.35)]'
                    : 'bg-white/25 hover:bg-white/40 w-2'
                }`}
                aria-label={t('onboarding.step', { current: i + 1, total: screens.length })}
              />
            ))}
          </div>

          {step < screens.length - 1 && (
            <button
              type="button"
              onClick={handleComplete}
              className="mt-8 text-slate-500 hover:text-slate-300 text-sm font-medium transition-colors"
            >
              {t('onboarding.skip')}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
