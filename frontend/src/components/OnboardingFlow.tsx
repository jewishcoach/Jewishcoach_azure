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
      icon: Sparkles,
      titleKey: 'onboarding.welcome.title',
      descKey: 'onboarding.welcome.desc',
      ctaKey: 'onboarding.next',
    },
    {
      icon: User,
      titleKey: 'onboarding.founder.title',
      descKey: 'onboarding.founder.desc',
      ctaKey: 'onboarding.next',
      linkKey: 'onboarding.learnMore',
      image: beniGalImg,
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
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(212,162,12,0.1),transparent_55%)]" aria-hidden />
      <div className="flex justify-end items-center gap-3 p-4 absolute top-0 end-0 z-10">
        <LanguageSwitcher />
        <UserButton afterSignOutUrl="/" />
      </div>
      <div className="flex-1 flex flex-col items-center justify-center p-6 relative z-[1]">
        <div className="max-w-lg w-full">
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
                  <img
                    src={currentScreen.image}
                    alt=""
                    className="w-40 h-40 md:w-48 md:h-48 rounded-full object-cover border-4 border-amber-400/25 shadow-lg"
                  />
                </div>
              ) : (
                <div className="inline-flex items-center justify-center w-[4.25rem] h-[4.25rem] rounded-2xl bg-amber-500/12 mb-8 ring-1 ring-amber-400/20">
                  <Icon className="w-9 h-9 text-amber-200" strokeWidth={1.5} />
                </div>
              )}
              <h1 className="text-2xl md:text-[1.75rem] font-semibold text-slate-50 mb-5 leading-snug tracking-tight">
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
                  className="inline-flex items-center gap-2 text-amber-300 hover:text-amber-200 text-sm font-medium mb-8 transition-colors"
                >
                  <ExternalLink className="w-4 h-4 shrink-0" />
                  {t(currentScreen.linkKey)}
                </a>
              )}

              <div className="flex flex-row gap-3 justify-center items-center flex-wrap">
                {step > 0 && (
                  <button
                    type="button"
                    onClick={() => setStep(step - 1)}
                    className="px-6 py-3.5 rounded-xl bg-white/10 text-slate-100 hover:bg-white/14 transition-colors text-base font-medium border border-white/10"
                  >
                    {t('onboarding.back')}
                  </button>
                )}
                <button
                  type="button"
                  onClick={isLast ? handleComplete : () => setStep(step + 1)}
                  className="inline-flex items-center gap-2 px-9 py-3.5 rounded-xl font-semibold text-base text-stone-950 bg-amber-500 hover:bg-amber-400 shadow-lg shadow-amber-950/25 transition-colors"
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
                  i === step ? 'bg-amber-400 w-8' : 'bg-white/25 hover:bg-white/40 w-2'
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
