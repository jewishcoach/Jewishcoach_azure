import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight,
  BookOpen,
  Compass,
  Heart,
  Send,
  Sparkles,
  Target,
  Users,
  ChevronLeft,
} from 'lucide-react';
import { LanguageSwitcher } from './LanguageSwitcher';
import { setOnboardingComplete } from '../lib/onboardingStorage';
import {
  clearIntroDraft,
  saveIntroDraft,
  type IntroDraftV1,
  type IntroGender,
} from '../lib/introDraftStorage';

const ACCENT = '#B38728';
const ACCENT_SOFT = '#FCF6BA';
const BG_PAGE = '#fafafa';
const BG_CHAT = '#f4f4f5';
const TEXT_MUTED = '#64748b';
const TEXT_BODY = '#1e293b';

type FlowStep = 'welcome' | 'identity' | 'intentions';
type IdentityPhase = 'name' | 'age' | 'gender';

type ChatMsg = { role: 'assistant' | 'user'; text: string };

const INTENTION_ICONS = {
  find_calm: Heart,
  clarity: Compass,
  patterns: Target,
  daily_practice: BookOpen,
  relationships: Users,
  spiritual_growth: Sparkles,
} as const;

type IntentionId = keyof typeof INTENTION_ICONS;

const INTENTION_IDS = Object.keys(INTENTION_ICONS) as IntentionId[];

function WelcomeVisual() {
  return (
    <div className="relative mx-auto mb-10 flex h-44 w-44 items-center justify-center">
      <div
        className="pointer-events-none absolute inset-0 scale-125 rounded-full opacity-70 blur-2xl"
        style={{ background: `radial-gradient(circle, ${ACCENT_SOFT} 0%, transparent 70%)` }}
        aria-hidden
      />
      <div
        className="relative h-24 w-24 rounded-full shadow-lg ring-4 ring-white/90"
        style={{
          background: `linear-gradient(145deg, #BF953F 0%, ${ACCENT} 55%, #8a6220 100%)`,
        }}
      />
      <svg
        className="pointer-events-none absolute h-36 w-36 text-amber-600/25"
        viewBox="0 0 120 120"
        aria-hidden
      >
        <circle
          cx="60"
          cy="60"
          r="52"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeDasharray="6 10"
        />
      </svg>
    </div>
  );
}

export interface AcquaintanceFlowProps {
  onComplete: () => void;
  /** When false (e.g. tunnel demo), do not persist intro draft for post-login sync. */
  persistDraft?: boolean;
  /**
   * fullscreen — legacy whole viewport.
   * embedded — fills parent height (use inside `AcquaintanceModalShell`).
   */
  layout?: 'fullscreen' | 'embedded';
}

/** Fixed overlay + blurred backdrop; children should be `AcquaintanceFlow` with layout="embedded". */
export function AcquaintanceModalShell({
  children,
  ariaLabel,
}: {
  children: ReactNode;
  ariaLabel: string;
}) {
  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-3 sm:p-6"
      role="presentation"
    >
      <div className="absolute inset-0 bg-slate-950/45 backdrop-blur-md" aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        className="relative flex h-[min(90dvh,820px)] w-full max-w-[440px] flex-col overflow-hidden rounded-[28px] shadow-[0_25px_80px_-12px_rgba(0,0,0,0.55)] ring-1 ring-black/15"
      >
        {children}
      </div>
    </div>
  );
}

export function AcquaintanceFlow({
  onComplete,
  persistDraft = true,
  layout = 'fullscreen',
}: AcquaintanceFlowProps) {
  const { t, i18n } = useTranslation();
  const isHe = i18n.language.startsWith('he');
  const dir = isHe ? 'rtl' : 'ltr';

  const [step, setStep] = useState<FlowStep>('welcome');
  const [identityPhase, setIdentityPhase] = useState<IdentityPhase>('name');
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState('');
  const [name, setName] = useState('');
  const [ageNum, setAgeNum] = useState<number | null>(null);
  const [gender, setGender] = useState<IntroGender | null>(null);
  const [intentions, setIntentions] = useState<IntentionId[]>([]);

  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, step, identityPhase, scrollToBottom]);

  useEffect(() => {
    if (step !== 'identity' || messages.length > 0) return;
    setMessages([{ role: 'assistant', text: t('acquaintance.chat.nameAsk') }]);
  }, [step, messages.length, t]);

  const appendPair = (userText: string, assistantText: string) => {
    setMessages((prev) => [...prev, { role: 'user', text: userText }, { role: 'assistant', text: assistantText }]);
  };

  const submitName = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    setName(trimmed);
    setInput('');
    appendPair(trimmed, t('acquaintance.chat.ageAsk', { name: trimmed }));
    setIdentityPhase('age');
  };

  const submitAge = () => {
    const n = parseInt(input.trim(), 10);
    if (Number.isNaN(n) || n < 13 || n > 120) return;
    setAgeNum(n);
    setInput('');
    appendPair(String(n), t('acquaintance.chat.genderAsk'));
    setIdentityPhase('gender');
  };

  const pickGender = (g: IntroGender) => {
    setGender(g);
    const labelKey =
      g === 'female'
        ? 'acquaintance.gender.female'
        : g === 'male'
          ? 'acquaintance.gender.male'
          : g === 'non_binary'
            ? 'acquaintance.gender.nonBinary'
            : 'acquaintance.gender.preferNot';
    setMessages((prev) => [...prev, { role: 'user', text: t(labelKey) }]);
    setStep('intentions');
  };

  const toggleIntention = (id: IntentionId) => {
    setIntentions((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });
  };

  const finishIntentions = () => {
    if (intentions.length === 0 || !gender || ageNum === null || !name.trim()) return;

    const draft: IntroDraftV1 = {
      version: 1,
      displayName: name.trim(),
      age: ageNum,
      gender,
      intentions: [...intentions],
      completed: true,
    };
    if (persistDraft) {
      saveIntroDraft(draft);
    } else {
      clearIntroDraft();
    }
    setOnboardingComplete();
    onComplete();
  };

  const skipIntro = () => {
    clearIntroDraft();
    setOnboardingComplete();
    onComplete();
  };

  const genderOptions: { id: IntroGender; labelKey: string }[] = [
    { id: 'female', labelKey: 'acquaintance.gender.female' },
    { id: 'male', labelKey: 'acquaintance.gender.male' },
    { id: 'non_binary', labelKey: 'acquaintance.gender.nonBinary' },
    { id: 'prefer_not', labelKey: 'acquaintance.gender.preferNot' },
  ];

  const rootScreen =
    layout === 'embedded' ? 'relative flex h-full min-h-0 flex-col' : 'relative flex min-h-screen flex-col';

  if (step === 'welcome') {
    return (
      <div
        className={`${rootScreen} items-center justify-center overflow-y-auto px-6 ${layout === 'embedded' ? 'py-8 sm:py-10' : 'py-14'}`}
        dir={dir}
        style={{ backgroundColor: BG_PAGE, fontFamily: '"Inter", system-ui, sans-serif' }}
      >
        <div className="absolute end-4 top-4 z-20 flex gap-2">
          <LanguageSwitcher />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="relative z-10 w-full max-w-md text-center"
        >
          <WelcomeVisual />

          <h1
            className="mb-4 text-[1.65rem] leading-snug tracking-tight sm:text-3xl"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif', color: '#0f172a' }}
          >
            <span>{t('acquaintance.welcome.line1')}</span>{' '}
            <span style={{ color: ACCENT, fontStyle: 'italic' }}>{t('acquaintance.welcome.accent')}</span>
            <span>{t('acquaintance.welcome.period')}</span>
          </h1>

          <p className="mb-12 text-base leading-relaxed sm:text-lg" style={{ color: TEXT_MUTED }}>
            {t('acquaintance.welcome.sub')}
          </p>

          <motion.button
            type="button"
            whileTap={{ scale: 0.992 }}
            onClick={() => setStep('identity')}
            className="w-full max-w-sm rounded-full px-10 py-4 text-base font-semibold shadow-md transition-[filter] hover:brightness-[1.03] sm:w-auto"
            style={{ backgroundColor: ACCENT, color: '#0f172a' }}
          >
            {t('acquaintance.welcome.cta')}
          </motion.button>

          <button
            type="button"
            onClick={skipIntro}
            className="mt-8 text-sm font-medium transition-colors hover:opacity-80"
            style={{ color: TEXT_MUTED }}
          >
            {t('acquaintance.skipToSignIn')}
          </button>
        </motion.div>
      </div>
    );
  }

  if (step === 'identity') {
    const showGenderChips = identityPhase === 'gender';
    const placeholder =
      identityPhase === 'name'
        ? t('acquaintance.chat.placeholderName')
        : identityPhase === 'age'
          ? t('acquaintance.chat.placeholderAge')
          : t('acquaintance.chat.placeholderLocked');

    const onSend = () => {
      if (identityPhase === 'name') submitName();
      else if (identityPhase === 'age') submitAge();
    };

    return (
      <div
        className={layout === 'embedded' ? 'flex h-full min-h-0 flex-col' : 'flex min-h-screen flex-col'}
        dir={dir}
        style={{ backgroundColor: BG_CHAT, fontFamily: '"Inter", system-ui, sans-serif' }}
      >
        <header className="flex shrink-0 items-center gap-3 border-b border-black/[0.06] bg-white/90 px-4 py-3 backdrop-blur-md">
          <button
            type="button"
            onClick={() => {
              setStep('welcome');
              setMessages([]);
              setIdentityPhase('name');
              setInput('');
              setName('');
              setAgeNum(null);
              setGender(null);
            }}
            className="rounded-full p-2 text-slate-600 transition-colors hover:bg-black/[0.05]"
            aria-label={t('acquaintance.back')}
          >
            <ChevronLeft className={`h-5 w-5 ${isHe ? 'rotate-180' : ''}`} />
          </button>
          <span className="font-medium text-slate-800">{t('acquaintance.identityTitle')}</span>
          <div className="ms-auto">
            <LanguageSwitcher />
          </div>
        </header>

        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
            <AnimatePresence initial={false}>
              {messages.map((m, i) => (
                <motion.div
                  key={`${i}-${m.role}-${m.text.slice(0, 12)}`}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-[15px] leading-relaxed shadow-sm ${
                      m.role === 'user'
                        ? 'rounded-ee-sm text-slate-900'
                        : 'rounded-es-sm bg-white text-slate-800 ring-1 ring-black/[0.06]'
                    }`}
                    style={
                      m.role === 'user'
                        ? { backgroundColor: ACCENT_SOFT, border: `1px solid ${ACCENT}33` }
                        : undefined
                    }
                  >
                    {m.text}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {showGenderChips && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex flex-wrap gap-2 ${isHe ? 'justify-end' : 'justify-start'} px-1`}
              >
                {genderOptions.map(({ id, labelKey }) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => pickGender(id)}
                    className="rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-800 shadow-sm transition-all hover:border-amber-300 hover:bg-amber-50/50"
                  >
                    {t(labelKey)}
                  </button>
                ))}
              </motion.div>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="shrink-0 border-t border-black/[0.06] bg-white px-4 py-4">
            <div className="mx-auto flex max-w-lg items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 py-2 shadow-inner">
              <input
                type={identityPhase === 'age' ? 'number' : 'text'}
                min={identityPhase === 'age' ? 13 : undefined}
                max={identityPhase === 'age' ? 120 : undefined}
                disabled={showGenderChips}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !showGenderChips) onSend();
                }}
                placeholder={placeholder}
                className="min-h-[44px] flex-1 bg-transparent text-[15px] outline-none placeholder:text-slate-400 disabled:opacity-45"
                style={{ color: TEXT_BODY }}
              />
              <button
                type="button"
                disabled={showGenderChips || !input.trim()}
                onClick={onSend}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition-opacity disabled:opacity-35"
                style={{ backgroundColor: ACCENT, color: '#0f172a' }}
                aria-label={t('chat.send')}
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const firstName = name.trim().split(/\s+/)[0] || name.trim();

  return (
    <div
      className={layout === 'embedded' ? 'flex h-full min-h-0 flex-col' : 'flex min-h-screen flex-col'}
      dir={dir}
      style={{ backgroundColor: BG_CHAT, fontFamily: '"Inter", system-ui, sans-serif' }}
    >
      <header className="flex shrink-0 items-center gap-3 border-b border-black/[0.06] bg-white/90 px-4 py-3 backdrop-blur-md">
        <button
          type="button"
          onClick={() => {
            setStep('identity');
            setIdentityPhase('gender');
          }}
          className="rounded-full p-2 text-slate-600 transition-colors hover:bg-black/[0.05]"
          aria-label={t('acquaintance.back')}
        >
          <ChevronLeft className={`h-5 w-5 ${isHe ? 'rotate-180' : ''}`} />
        </button>
        <span className="font-medium text-slate-800">{t('acquaintance.intentionsTitle')}</span>
        <div className="ms-auto">
          <LanguageSwitcher />
        </div>
      </header>

      <div className="flex flex-1 flex-col overflow-y-auto px-4 py-8">
        <div className="mx-auto w-full max-w-lg">
          <div className="mb-8 flex gap-3">
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-slate-700 to-slate-900 shadow-md"
              aria-hidden
            >
              <Sparkles className="h-5 w-5 text-amber-200/90" />
            </div>
            <div className="rounded-2xl rounded-ss-sm bg-white px-4 py-3 text-[15px] leading-relaxed text-slate-800 shadow-sm ring-1 ring-black/[0.06]">
              {t('acquaintance.intentionsLead', { name: firstName })}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            {INTENTION_IDS.map((id) => {
              const Icon = INTENTION_ICONS[id];
              const sel = intentions.includes(id);
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => toggleIntention(id)}
                  className={`flex min-h-[120px] flex-col items-center justify-center gap-3 rounded-2xl border px-3 py-4 text-center transition-all ${
                    sel
                      ? 'border-transparent shadow-md'
                      : 'border-slate-200 bg-white shadow-sm hover:border-amber-200/80'
                  }`}
                  style={
                    sel
                      ? {
                          backgroundColor: ACCENT,
                          color: '#fff',
                        }
                      : { color: TEXT_BODY }
                  }
                >
                  <Icon className={`h-7 w-7 ${sel ? 'text-white' : 'text-slate-600'}`} strokeWidth={1.5} />
                  <span className={`text-sm font-semibold leading-snug ${sel ? 'text-white' : ''}`}>
                    {t(`acquaintance.intention.${id}.title`)}
                  </span>
                </button>
              );
            })}
          </div>

          <p className="mt-4 text-center text-xs" style={{ color: TEXT_MUTED }}>
            {t('acquaintance.intentionsHint')}
          </p>

          <motion.button
            type="button"
            disabled={intentions.length === 0}
            whileTap={{ scale: intentions.length ? 0.992 : 1 }}
            onClick={finishIntentions}
            className="mt-10 flex w-full items-center justify-center gap-2 rounded-full py-4 text-base font-semibold shadow-md transition-[filter] disabled:cursor-not-allowed disabled:opacity-45"
            style={{ backgroundColor: ACCENT, color: '#fff' }}
          >
            {t('acquaintance.continue')}
            <ArrowRight className={`h-5 w-5 ${isHe ? 'rotate-180' : ''}`} />
          </motion.button>
        </div>
      </div>
    </div>
  );
}
