import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useTranslation } from 'react-i18next';
import {
  ArrowRight,
  CalendarDays,
  CircleHelp,
  Compass,
  Crosshair,
  Flame,
  Heart,
  Lightbulb,
  Mic,
  Sparkles,
  TrendingUp,
  UserRound,
  Users,
  Waypoints,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { LanguageSwitcher } from './LanguageSwitcher';
import { WORKSPACE_CHAT_FONT } from '../constants/workspaceFonts';
import { apiClient } from '../services/api';

type Props = {
  onComplete: () => void;
  initialDisplayName?: string | null;
  onDisplayNameUpdated?: (name: string) => void;
};

type Phase = 'name' | 'goal' | 'experience' | 'pace' | 'summary';

type ChatMsg = {
  id: string;
  role: 'coach' | 'user';
  text: string;
};

const STEPS = 4;

function cx(...parts: (string | false | undefined | null)[]) {
  return parts.filter(Boolean).join(' ');
}

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function extractPreferredName(text: string): string {
  const s = text.trim();
  if (!s) return '';
  const en =
    /\b(?:i'?m|i am|call me|my name is|name(?:'s| is)?)\s+([^\s,!?.]+)/i.exec(s);
  if (en?.[1]) return en[1].slice(0, 48);
  const he = /(?:אני|קוראים לי|שמי)\s+([^\s,!?.]+)/u.exec(s);
  if (he?.[1]) return he[1].slice(0, 48);
  const parts = s.split(/[\s,]+/).filter(Boolean);
  return parts[0]?.slice(0, 48) ?? '';
}

function phaseStep(p: Phase): number {
  if (p === 'summary') return STEPS;
  const map: Record<Exclude<Phase, 'summary'>, number> = {
    name: 1,
    goal: 2,
    experience: 3,
    pace: 4,
  };
  return map[p];
}

const GOAL_IDS = ['peace', 'confidence', 'knowSelf', 'pattern'] as const;
type GoalId = (typeof GOAL_IDS)[number];

const EXP_IDS = ['coached', 'new', 'self', 'unsure'] as const;
type ExpId = (typeof EXP_IDS)[number];

const PACE_IDS = ['gentle', 'weekly', 'immersive', 'focused'] as const;
type PaceId = (typeof PACE_IDS)[number];

const GOAL_ICONS: Record<GoalId, LucideIcon> = {
  peace: Sparkles,
  confidence: TrendingUp,
  knowSelf: UserRound,
  pattern: Waypoints,
};

const EXP_ICONS: Record<ExpId, LucideIcon> = {
  coached: Users,
  new: Lightbulb,
  self: Compass,
  unsure: CircleHelp,
};

const PACE_ICONS: Record<PaceId, LucideIcon> = {
  gentle: Heart,
  weekly: CalendarDays,
  immersive: Flame,
  focused: Crosshair,
};

function CoachAvatarBadge({
  variant = 'thread',
  letter = 'C',
}: {
  variant?: 'thread' | 'header';
  letter?: string;
}) {
  const header = variant === 'header';
  return (
    <div
      className={cx(
        'flex flex-shrink-0 items-center justify-center rounded-full font-medium text-[#0e1117]',
        header ? 'h-[35px] w-[35px] bg-[#C8953A] text-[14.375px]' : 'h-[22px] w-[22px] bg-[#FFB022] text-[10px]',
      )}
      aria-hidden
    >
      {letter}
    </div>
  );
}

function CoachRow({
  variant = 'thread',
  label,
}: {
  variant?: 'thread' | 'header';
  label: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <CoachAvatarBadge variant={variant === 'header' ? 'header' : 'thread'} />
      <span
        className="text-[12px] uppercase tracking-[1px] text-[#4c5a70]"
        style={{ fontFamily: 'Inter, sans-serif' }}
      >
        {label}
      </span>
    </div>
  );
}

function ChoiceCard({
  icon: Icon,
  label,
  selected,
  onClick,
  disabled,
}: {
  icon: LucideIcon;
  label: string;
  selected?: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cx(
        'flex h-[107px] w-full flex-col items-center justify-center gap-1 rounded-[18px] border bg-white px-3 py-3 text-center shadow-[0px_1px_8px_rgba(10,10,10,0.06)] transition-colors md:w-[210px]',
        selected
          ? 'border-[#C8953A] shadow-[0px_1px_28px_rgba(212,160,23,0.2)]'
          : 'border-[#E8E0CC] hover:border-[#d4c4a8]',
        disabled && 'pointer-events-none opacity-60',
      )}
      style={{ fontFamily: 'Inter, sans-serif' }}
    >
      <Icon
        className={cx('h-8 w-8', selected ? 'text-[#C8953A]' : 'text-[#6b7280]')}
        strokeWidth={1.35}
      />
      <span className="text-[14px] font-medium leading-[30px] text-[#393939]">{label}</span>
    </button>
  );
}

function LeftDecorPanel({
  tagline,
  headlineBefore,
  headlineAccent,
  subtitle,
}: {
  tagline: string;
  headlineBefore: string;
  headlineAccent: string;
  subtitle: string;
}) {
  return (
    <div className="relative hidden min-h-0 w-full flex-shrink-0 flex-col overflow-hidden bg-[#1C2636] md:flex md:w-[min(520px,38vw)] md:min-w-[300px] md:max-w-[520px]">
      <div className="pointer-events-none absolute inset-0">
        <div
          className="absolute inset-0"
          style={{
            background:
              'radial-gradient(60% 60% at 50% 45%, rgba(201, 169, 110, 0.18) 0%, rgba(12, 16, 24, 0) 100%), radial-gradient(50% 50% at 30% 70%, rgba(74, 111, 165, 0.1) 0%, rgba(12, 16, 24, 0) 100%)',
          }}
        />
        <svg
          className="absolute left-1/2 top-[18%] h-[58%] w-[90%] max-w-[420px] -translate-x-1/2 text-[rgba(201,169,110,0.12)]"
          viewBox="0 0 100 100"
          fill="none"
          aria-hidden
        >
          <polygon points="50,12 88,82 12,82" stroke="currentColor" strokeWidth="0.8" />
          <polygon points="50,88 12,18 88,18" stroke="currentColor" strokeWidth="0.8" />
          <circle cx="50" cy="50" r="3.2" fill="#C9A96E" fillOpacity={0.55} />
          <circle cx="50" cy="26" r="2.4" fill="#C9A96E" fillOpacity={0.45} />
          <circle cx="50" cy="74" r="2.4" fill="#C9A96E" fillOpacity={0.45} />
          <circle cx="29" cy="68" r="2.4" fill="#C9A96E" fillOpacity={0.45} />
          <circle cx="71" cy="68" r="2.4" fill="#C9A96E" fillOpacity={0.45} />
          <circle cx="29" cy="32" r="2.4" fill="#C9A96E" fillOpacity={0.45} />
          <circle cx="71" cy="32" r="2.4" fill="#C9A96E" fillOpacity={0.45} />
        </svg>
      </div>

      <div className="relative z-10 flex min-h-0 flex-1 flex-col px-10 pb-10 pt-[max(1.5rem,env(safe-area-inset-top))]">
        <div className="flex items-center gap-[9px]">
          <img src="/bsd-logo.png" alt="" className="h-8 w-[34px] object-contain opacity-90" />
          <div className="h-[18px] w-px bg-white/[0.11]" aria-hidden />
          <p
            className="font-medium leading-4 text-[#f0f4fa]"
            dir="rtl"
            style={{
              fontFamily: '"Cormorant Garamond", Georgia, serif',
              fontSize: 16,
            }}
          >
            {tagline}
          </p>
        </div>

        <div className="mt-auto flex flex-col items-center gap-2 px-2 pb-4 text-center md:pb-8">
          <h2
            className="max-w-[320px] font-semibold leading-[46px] text-[#ede9e0]"
            style={{
              fontFamily: '"Cormorant Garamond", Georgia, serif',
              fontSize: 44,
            }}
          >
            <span className="block">{headlineBefore}</span>
            <span className="block text-[#C9A96E]">{headlineAccent}</span>
          </h2>
          <p
            className="max-w-[329px] text-[13px] font-normal leading-[21px] text-white/[0.55]"
            style={{ fontFamily: 'Inter, sans-serif' }}
          >
            {subtitle}
          </p>
        </div>
      </div>
    </div>
  );
}

function ChatBubble({
  role,
  children,
}: {
  role: 'coach' | 'user';
  children: ReactNode;
}) {
  const coach = role === 'coach';
  return (
    <div
      className={cx(
        'max-w-[min(497px,92vw)] rounded-[4px_18px_18px_18px] border border-[#E8E0CC] bg-white px-6 py-4 shadow-[0px_1px_8px_rgba(10,10,10,0.06)]',
        coach ? 'text-[#393939]' : 'text-[#1a1510]',
      )}
      style={{ fontFamily: 'Inter, sans-serif', fontSize: 16, lineHeight: 1.85 }}
    >
      {children}
    </div>
  );
}

export function BsdOnboardingFlow({
  onComplete,
  initialDisplayName = null,
  onDisplayNameUpdated,
}: Props) {
  const { t, i18n } = useTranslation();
  const titleId = useId();
  const isHe = i18n.language.startsWith('he');
  const dir: 'rtl' | 'ltr' = isHe ? 'rtl' : 'ltr';

  const [phase, setPhase] = useState<Phase>('name');
  const [input, setInput] = useState('');
  const [preferredName, setPreferredName] = useState('');
  const [goalId, setGoalId] = useState<GoalId | null>(null);
  const [expId, setExpId] = useState<ExpId | null>(null);
  const [paceId, setPaceId] = useState<PaceId | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [seeded, setSeeded] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const step = phaseStep(phase);

  useEffect(() => {
    if (seeded) return;
    setMessages([
      { id: uid(), role: 'coach', text: t('bsdOnboarding.coachPing') },
      { id: uid(), role: 'coach', text: t('bsdOnboarding.coachAskName') },
    ]);
    setSeeded(true);
  }, [seeded, t]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, phase]);

  const coachLabel = t('bsdOnboarding.coachLabel');
  const brandTitle = t('bsdOnboarding.brandTitle');

  const submitName = useCallback(async () => {
    let name = extractPreferredName(input).trim();
    if (!name) name = input.trim().slice(0, 48);
    if (!name && initialDisplayName?.trim()) name = initialDisplayName.trim().slice(0, 48);
    if (!name) return;

    setInput('');
    setPreferredName(name);

    try {
      await apiClient.updateProfile({ display_name: name });
      onDisplayNameUpdated?.(name);
    } catch {
      /* best-effort */
    }

    setMessages((m) => [
      ...m,
      { id: uid(), role: 'user', text: name },
      { id: uid(), role: 'coach', text: t('bsdOnboarding.coachAskGoal', { name }) },
    ]);
    setPhase('goal');
  }, [initialDisplayName, input, onDisplayNameUpdated, t]);

  const pickGoal = useCallback(
    (id: GoalId) => {
      if (phase !== 'goal' || goalId) return;
      setGoalId(id);
      const label = t(`bsdOnboarding.goal.${id}`);
      setMessages((m) => [
        ...m,
        { id: uid(), role: 'user', text: label },
        { id: uid(), role: 'coach', text: t('bsdOnboarding.coachAskExp') },
      ]);
      setPhase('experience');
    },
    [goalId, phase, t],
  );

  const pickExp = useCallback(
    (id: ExpId) => {
      if (phase !== 'experience' || expId) return;
      setExpId(id);
      const label = t(`bsdOnboarding.exp.${id}`);
      setMessages((m) => [
        ...m,
        { id: uid(), role: 'user', text: label },
        { id: uid(), role: 'coach', text: t('bsdOnboarding.coachAskPace') },
      ]);
      setPhase('pace');
    },
    [expId, phase, t],
  );

  const pickPace = useCallback(
    (id: PaceId) => {
      if (phase !== 'pace' || paceId) return;
      setPaceId(id);
      const label = t(`bsdOnboarding.pace.${id}`);
      setMessages((m) => [
        ...m,
        { id: uid(), role: 'user', text: label },
        {
          id: uid(),
          role: 'coach',
          text: t('bsdOnboarding.summaryCoach', {
            name: preferredName || t('bsdOnboarding.fallbackName'),
          }),
        },
      ]);
      setPhase('summary');
    },
    [paceId, phase, preferredName, t],
  );

  const enterWorkspace = useCallback(async () => {
    try {
      await apiClient.patchUserPreferences({
        bsd_intro_screens_completed: true,
        bsd_onboard_goal: goalId ?? undefined,
        bsd_onboard_experience: expId ?? undefined,
        bsd_onboard_pace: paceId ?? undefined,
      });
    } catch {
      /* App.tsx retries completion */
    }
    onComplete();
  }, [expId, goalId, onComplete, paceId]);

  const showComposer = phase !== 'summary';

  return (
    <div
      className="fixed inset-0 z-[100] flex flex-col overflow-hidden bg-[#FAF8F3]"
      style={{ fontFamily: WORKSPACE_CHAT_FONT }}
      dir={dir}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <span id={titleId} className="sr-only">
        {t('bsdOnboarding.a11yTitle')}
      </span>

      <div className="flex justify-end px-4 pt-[max(0.5rem,env(safe-area-inset-top))] md:absolute md:right-4 md:top-3 md:z-30">
        <LanguageSwitcher />
      </div>

      {/* Mobile strip */}
      <div className="flex shrink-0 items-center gap-2 border-b border-white/[0.06] bg-[#1C2636] px-4 py-3 md:hidden">
        <img src="/bsd-logo.png" alt="" className="h-7 w-8 object-contain opacity-90" />
        <p
          className="flex-1 truncate text-center text-[13px] font-medium text-[#ede9e0]"
          dir="rtl"
          style={{ fontFamily: '"Cormorant Garamond", Georgia, serif' }}
        >
          {t('bsdOnboarding.tagline')}
        </p>
      </div>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <LeftDecorPanel
          tagline={t('bsdOnboarding.tagline')}
          headlineBefore={t('bsdOnboarding.headlineBefore')}
          headlineAccent={t('bsdOnboarding.headlineAccent')}
          subtitle={t('bsdOnboarding.leftSubtitle')}
        />

        <section
          className="flex min-h-0 min-w-0 flex-1 flex-col bg-[#FAF8F3]"
          aria-label={t('bsdOnboarding.chatSection')}
        >
          {/* TOPBAR */}
          <header className="flex h-[66px] shrink-0 items-center justify-between gap-4 bg-[#1E293B] px-4 md:px-[70px]">
            <div className="flex min-w-0 items-center gap-3">
              <CoachAvatarBadge variant="header" />
              <div className="flex min-w-0 flex-col gap-1">
                <span
                  className="truncate text-[16px] font-medium leading-none text-[#EDE9E0]"
                  style={{ fontFamily: 'Inter, sans-serif' }}
                >
                  {brandTitle}
                </span>
                <div className="flex items-center gap-1">
                  <span className="h-[5px] w-[5px] shrink-0 rounded-full bg-[#C8953A]" aria-hidden />
                  <span className="text-[10px] font-normal leading-none text-[#C8953A]">
                    {t('bsdOnboarding.availableNow')}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex flex-col items-end gap-[7px]">
              <span className="text-[14px] text-white/[0.55]" style={{ fontFamily: 'Inter, sans-serif' }}>
                {t('bsdOnboarding.step', { current: step, total: STEPS })}
              </span>
              <div className="flex gap-[6px]" role="progressbar" aria-valuenow={step} aria-valuemin={1} aria-valuemax={STEPS}>
                {Array.from({ length: STEPS }, (_, i) => (
                  <span
                    key={i}
                    className={cx(
                      'h-[3px] w-5 rounded-[50px]',
                      i < step ? 'bg-[#C8953A]' : 'bg-[#424345]',
                    )}
                  />
                ))}
              </div>
            </div>
          </header>

          <div
            ref={scrollRef}
            className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-4 md:px-12 md:py-6"
          >
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cx(
                  'flex w-full flex-col gap-2',
                  msg.role === 'coach' ? 'items-start' : 'items-end',
                )}
              >
                {msg.role === 'coach' ? (
                  <>
                    <CoachRow label={coachLabel} />
                    <ChatBubble role="coach">{msg.text}</ChatBubble>
                  </>
                ) : (
                  <ChatBubble role="user">{msg.text}</ChatBubble>
                )}
              </div>
            ))}

            {phase === 'goal' && (
              <div className="flex w-full justify-center md:justify-start">
                <div className="grid w-full max-w-[432px] grid-cols-2 gap-3">
                  {GOAL_IDS.map((id) => (
                    <ChoiceCard
                      key={id}
                      icon={GOAL_ICONS[id]}
                      label={t(`bsdOnboarding.goal.${id}`)}
                      selected={goalId === id}
                      disabled={!!goalId && goalId !== id}
                      onClick={() => pickGoal(id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {phase === 'experience' && (
              <div className="flex w-full justify-center md:justify-start">
                <div className="grid w-full max-w-[432px] grid-cols-2 gap-3">
                  {EXP_IDS.map((id) => (
                    <ChoiceCard
                      key={id}
                      icon={EXP_ICONS[id]}
                      label={t(`bsdOnboarding.exp.${id}`)}
                      selected={expId === id}
                      disabled={!!expId && expId !== id}
                      onClick={() => pickExp(id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {phase === 'pace' && (
              <div className="flex w-full justify-center md:justify-start">
                <div className="grid w-full max-w-[432px] grid-cols-2 gap-3">
                  {PACE_IDS.map((id) => (
                    <ChoiceCard
                      key={id}
                      icon={PACE_ICONS[id]}
                      label={t(`bsdOnboarding.pace.${id}`)}
                      selected={paceId === id}
                      disabled={!!paceId && paceId !== id}
                      onClick={() => pickPace(id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {phase === 'summary' && goalId && expId && paceId && (
              <div className="flex w-full flex-col items-center gap-5 pb-6 md:items-start">
                <div className="w-full max-w-[432px] rounded-2xl border border-[#E8E0CC] bg-white p-6 shadow-[0px_1px_8px_rgba(10,10,10,0.06)]">
                  <h3
                    className="text-lg font-medium text-[#1a1510]"
                    style={{ fontFamily: '"Cormorant Garamond", Georgia, serif' }}
                  >
                    {t('bsdOnboarding.summaryTitle')}
                  </h3>
                  <p className="mt-1 text-[14px] text-[#393939]/80">{t('bsdOnboarding.summarySubtitle')}</p>
                  <dl className="mt-4 space-y-3 text-[14px]">
                    <div className="flex justify-between gap-4 border-b border-[#E8E0CC]/80 pb-2">
                      <dt className="text-[#4c5a70]">{t('bsdOnboarding.summary.name')}</dt>
                      <dd className="text-end font-medium text-[#1a1510]">{preferredName}</dd>
                    </div>
                    <div className="flex justify-between gap-4 border-b border-[#E8E0CC]/80 pb-2">
                      <dt className="text-[#4c5a70]">{t('bsdOnboarding.summary.goal')}</dt>
                      <dd className="text-end font-medium text-[#1a1510]">{t(`bsdOnboarding.goal.${goalId}`)}</dd>
                    </div>
                    <div className="flex justify-between gap-4 border-b border-[#E8E0CC]/80 pb-2">
                      <dt className="text-[#4c5a70]">{t('bsdOnboarding.summary.exp')}</dt>
                      <dd className="text-end font-medium text-[#1a1510]">{t(`bsdOnboarding.exp.${expId}`)}</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-[#4c5a70]">{t('bsdOnboarding.summary.pace')}</dt>
                      <dd className="text-end font-medium text-[#1a1510]">{t(`bsdOnboarding.pace.${paceId}`)}</dd>
                    </div>
                  </dl>
                </div>
                <button
                  type="button"
                  onClick={() => void enterWorkspace()}
                  className="w-full max-w-[432px] rounded-[11px] bg-[#1E293B] py-3 text-[15px] font-medium text-white shadow-sm transition hover:bg-[#151e2e]"
                  style={{ fontFamily: 'Inter, sans-serif' }}
                >
                  {t('bsdOnboarding.enterSpace')}
                </button>
              </div>
            )}
          </div>

          <div className="h-0.5 w-full shrink-0 bg-[#E8E0CC]" aria-hidden />

          {showComposer ? (
            <footer className="shrink-0 bg-[#FAF8F3] px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3 md:px-12">
              <div className="flex h-12 items-center gap-2 rounded-[11px] border border-[#E8E0CC] bg-white px-3 shadow-sm">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && phase === 'name') {
                      e.preventDefault();
                      void submitName();
                    }
                  }}
                  disabled={phase !== 'name'}
                  placeholder={t('bsdOnboarding.inputPlaceholder')}
                  className="min-w-0 flex-1 bg-transparent text-[14px] font-light text-[#4c5a70] outline-none placeholder:text-[#4c5a70]/70 disabled:opacity-50"
                  style={{ fontFamily: 'Inter, sans-serif' }}
                  aria-label={t('bsdOnboarding.inputAria')}
                />
                <button
                  type="button"
                  disabled
                  className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-[7px] border border-white/[0.11] bg-[#E8E0CC] opacity-50"
                  aria-label={t('bsdOnboarding.micAria')}
                >
                  <Mic className="h-[13px] w-[13px] text-[#4c5a70]" strokeWidth={2} />
                </button>
                <button
                  type="button"
                  onClick={() => void submitName()}
                  disabled={phase !== 'name'}
                  className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-[7px] bg-[#1E293B] disabled:opacity-40"
                  aria-label={t('bsdOnboarding.sendAria')}
                >
                  <ArrowRight className="h-[13px] w-[13px] text-white" strokeWidth={2} />
                </button>
              </div>
            </footer>
          ) : (
            <footer className="h-3 shrink-0 bg-[#FAF8F3] pb-[max(0.5rem,env(safe-area-inset-bottom))]" />
          )}
        </section>
      </div>
    </div>
  );
}
