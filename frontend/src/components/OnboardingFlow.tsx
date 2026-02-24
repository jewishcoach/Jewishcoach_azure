import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { UserButton } from '@clerk/clerk-react';
import { Sparkles, MessageCircle, BookOpen, User, ChevronRight, ExternalLink } from 'lucide-react';
import { LanguageSwitcher } from './LanguageSwitcher';

const ONBOARDING_STORAGE_KEY = 'jewishcoach_onboarding_seen';

export function hasSeenOnboarding(): boolean {
  return localStorage.getItem(ONBOARDING_STORAGE_KEY) === 'true';
}

export function setOnboardingComplete(): void {
  localStorage.setItem(ONBOARDING_STORAGE_KEY, 'true');
}

interface OnboardingFlowProps {
  onComplete: () => void;
}

const BSD_COACH_URL = 'https://bsdcoach.com';

export function OnboardingFlow({ onComplete }: OnboardingFlowProps) {
  const { t, i18n } = useTranslation();
  const [step, setStep] = useState(0);
  const isHe = i18n.language === 'he';

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
      icon: User,
      titleKey: 'onboarding.founder.title',
      descKey: 'onboarding.founder.desc',
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
    <div className="min-h-screen bg-[#020617] flex flex-col relative" dir={isHe ? 'rtl' : 'ltr'}>
      <div className="flex justify-end items-center gap-3 p-4 absolute top-0 end-0 z-10">
        <LanguageSwitcher />
        <UserButton afterSignOutUrl="/" />
      </div>
      <div className="flex-1 flex flex-col items-center justify-center p-6">
      <div className="max-w-lg w-full">
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: isHe ? 20 : -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: isHe ? -20 : 20 }}
            transition={{ duration: 0.3 }}
            className="text-center"
          >
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[#FCF6BA]/15 mb-8">
              <Icon className="w-8 h-8 text-[#FCF6BA]" />
            </div>
            <h1 className="text-2xl md:text-3xl font-bold text-[#F5F5F0] mb-4" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              {t(currentScreen.titleKey)}
            </h1>
            <p className="text-[#F5F5F0]/85 text-base leading-relaxed mb-8" style={{ fontFamily: 'Inter, sans-serif' }}>
              {t(currentScreen.descKey)}
            </p>

            {currentScreen.linkKey && (
              <a
                href={BSD_COACH_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-[#FCF6BA] hover:text-[#FCF6BA]/80 text-sm mb-8 transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                {t(currentScreen.linkKey)}
              </a>
            )}

            <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
              {step > 0 && (
                <button
                  onClick={() => setStep(step - 1)}
                  className="px-6 py-3 rounded-lg bg-white/10 text-[#F5F5F0] hover:bg-white/15 transition-colors text-sm"
                >
                  {t('onboarding.back')}
                </button>
              )}
              <button
                onClick={isLast ? handleComplete : () => setStep(step + 1)}
                className="flex items-center gap-2 px-8 py-3 rounded-lg font-medium transition-colors"
                style={{
                  background: 'linear-gradient(45deg, #BF953F, #FCF6BA, #B38728)',
                  color: '#020617',
                }}
              >
                {t(currentScreen.ctaKey)}
                <ChevronRight className={`w-5 h-5 ${isHe ? 'rotate-180' : ''}`} />
              </button>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Progress dots */}
        <div className="flex justify-center gap-2 mt-12">
          {screens.map((_, i) => (
            <button
              key={i}
              onClick={() => setStep(i)}
              className={`w-2 h-2 rounded-full transition-colors ${
                i === step ? 'bg-[#FCF6BA] w-6' : 'bg-white/30 hover:bg-white/50'
              }`}
              aria-label={t('onboarding.step', { current: i + 1, total: screens.length })}
            />
          ))}
        </div>

        {/* Skip */}
        {step < screens.length - 1 && (
          <button
            onClick={handleComplete}
            className="mt-6 text-[#F5F5F0]/50 hover:text-[#F5F5F0]/80 text-sm transition-colors"
          >
            {t('onboarding.skip')}
          </button>
        )}
      </div>
      </div>
    </div>
  );
}
