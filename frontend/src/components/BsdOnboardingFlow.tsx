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
  Briefcase,
  Heart,
  Mic,
  Send,
  Sparkles,
  Sprout,
  Target,
  UserRound,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { LanguageSwitcher } from './LanguageSwitcher';
import { WORKSPACE_CHAT_FONT } from '../constants/workspaceFonts';
import { apiClient, type OnboardingKnownSlots } from '../services/api';
import { buildIntakeOpeningMessage } from '../utils/welcomeMessage';

type Props = {
  onComplete: () => void;
  initialDisplayName?: string | null;
  onDisplayNameUpdated?: (name: string) => void;
};

type ChatMsg = {
  id: string;
  role: 'coach' | 'user';
  text: string;
  showCoachMeta?: boolean;
};

const TOPIC_IDS = [
  'goals',
  'parenting',
  'relationships',
  'career',
  'wellbeing',
  'personal_growth',
] as const;
type TopicId = (typeof TOPIC_IDS)[number];

const GENDER_IDS = ['male', 'female'] as const;
type GenderId = (typeof GENDER_IDS)[number];

const STEPS = 3;

function cx(...parts: (string | false | undefined | null)[]) {
  return parts.filter(Boolean).join(' ');
}

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function isTopicId(s: string): s is TopicId {
  return (TOPIC_IDS as readonly string[]).includes(s);
}

function transcriptForApi(messages: ChatMsg[]) {
  return messages.map((m) => ({
    role: m.role === 'coach' ? ('assistant' as const) : ('user' as const),
    content: typeof m.text === 'string' ? m.text : '',
  }));
}

/**
 * First reply after "what's your name?" — if it looks like a name, send as known_slots.display_name
 * so the coach drops a wrong opener placeholder (not for quick-pick goal phrases).
 */
function stripIntakeNoise(text: string): string {
  return text.replace(/[\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, '').trim();
}

function guessDisplayNameFromFirstReply(text: string): string | undefined {
  const trimmed = stripIntakeNoise(text).replace(/(?:[.!?…])+$/u, '').trim();
  const t = trimmed;
  if (t.length < 2 || t.length > 48) return undefined;
  if (/[\n\r]/.test(t)) return undefined;
  if (/\d/.test(t)) return undefined;
  const words = t.split(/\s+/).filter(Boolean);
  if (words.length === 0 || words.length > 2) return undefined;
  const joined = words.join(' ');
  if (joined.length > 28) return undefined;
  const low = t.toLowerCase();
  if (low === 'זכר' || low === 'נקבה' || low === 'male' || low === 'female') return undefined;
  if (!/^[\p{L}\s\-'.]+$/u.test(t)) return undefined;
  return joined.slice(0, 80);
}

/** When strict guess fails (e.g. 3-word name), still send a single-line reply as display_name on turn 1. */
function looseNameFromFirstReply(text: string): string | undefined {
  const t = stripIntakeNoise(text).replace(/(?:[.!?…])+$/u, '').trim();
  if (t.length < 2 || t.length > 48 || /[\n\r]/.test(t) || /\d/.test(t)) return undefined;
  const low = t.toLowerCase();
  if (low === 'זכר' || low === 'נקבה' || low === 'male' || low === 'female') return undefined;
  const words = t.split(/\s+/).filter(Boolean);
  if (words.length < 1 || words.length > 3) return undefined;
  if (words.some((w) => w.length > 22)) return undefined;
  if (!/^[\p{L}\s\-'.]+$/u.test(t)) return undefined;
  return t.slice(0, 80);
}

/**
 * display_name sent in known_slots must include the name from an earlier line when the latest user
 * message is only a chip tap (gender/topic); React state alone can lag or miss edge cases.
 */
function displayNameForKnownSlotsPayload(
  historySnapshot: ChatMsg[],
  currentRaw: string,
  hintUsed: boolean,
): string | undefined {
  const tryLine = (raw: string): string | undefined => {
    const t = stripIntakeNoise(raw);
    return guessDisplayNameFromFirstReply(t) ?? looseNameFromFirstReply(t);
  };
  if (!hintUsed) {
    const cur = tryLine(currentRaw);
    if (cur) return cur.slice(0, 80);
  }
  const users = historySnapshot.filter((m) => m.role === 'user');
  const toScan = hintUsed ? users.slice(0, -1) : users;
  for (const m of toScan) {
    const stripped = stripIntakeNoise(m.text);
    const low = stripped.toLowerCase();
    if (low === 'זכר' || low === 'נקבה' || low === 'male' || low === 'female') continue;
    const n = tryLine(m.text);
    if (n) return n.slice(0, 80);
  }
  return undefined;
}

const TOPIC_ICONS: Record<TopicId, LucideIcon> = {
  goals: Target,
  parenting: Users,
  relationships: Heart,
  career: Briefcase,
  wellbeing: Sparkles,
  personal_growth: Sprout,
};

const GENDER_ICONS: Record<GenderId, LucideIcon> = {
  male: UserRound,
  female: Heart,
};

function CoachAvatarBadge({ letter = 'C' }: { letter?: string }) {
  return (
    <div
      className="flex h-[22px] w-[22px] flex-shrink-0 items-center justify-center rounded-full bg-[#FFB022] text-[10px] font-medium text-[#0e1117]"
      aria-hidden
    >
      {letter}
    </div>
  );
}

function CoachRow({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2">
      <CoachAvatarBadge />
      <span
        className="text-[12px] font-medium uppercase tracking-[1px] text-[#C9A96E]"
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
        'flex h-[107px] w-full min-w-0 flex-col items-center justify-center gap-1 rounded-[18px] border bg-white px-2 py-3 text-center shadow-[0px_1px_8px_rgba(10,10,10,0.06)] transition-colors sm:px-3',
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
  headlineBefore,
  headlineAccent,
  subtitle,
}: {
  headlineBefore: string;
  headlineAccent: string;
  subtitle: string;
}) {
  return (
    <div className="relative flex min-h-[min(168px,26svh)] w-full shrink-0 flex-col overflow-hidden bg-[#1C2636] md:min-h-0 md:w-[min(520px,36.1vw)] md:min-w-[300px] md:max-w-[520px]">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <img
          src="/bsd-onboarding-left-decor.svg"
          alt=""
          className="absolute left-1/2 top-[14%] h-[52%] w-[min(104%,520px)] max-w-none -translate-x-1/2 scale-[0.92] select-none object-contain opacity-[0.85] md:top-[10%] md:h-[72%] md:scale-100 md:opacity-100"
          draggable={false}
          aria-hidden
        />
      </div>
      <div className="relative z-10 flex min-h-0 flex-1 flex-col justify-center px-4 py-4 md:justify-end md:px-10 md:pb-10 md:pt-10">
        <div className="flex flex-col items-center gap-1.5 px-1 text-center md:gap-3 md:px-2 md:pb-2 md:pt-0">
          <h2
            className="max-w-[min(320px,92vw)] font-semibold leading-[1.06] text-[#ede9e0] text-[clamp(1.5rem,5.4vw,2.75rem)] md:leading-[1.05]"
            style={{
              fontFamily: '"Cormorant Garamond", Georgia, serif',
            }}
          >
            <span className="block">{headlineBefore}</span>
            <span className="block text-[#C9A96E]">{headlineAccent}</span>
          </h2>
          <p
            className="max-w-[min(329px,92vw)] text-[11px] font-normal leading-snug text-white/[0.55] md:text-[13px] md:leading-[21px]"
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

function TypingIndicator({ label }: { label: string }) {
  return (
    <div className="flex w-full flex-col items-start gap-2">
      <CoachRow label={label} />
      <div
        className="rounded-[4px_18px_18px_18px] border border-[#E8E0CC] bg-white px-5 py-3 shadow-[0px_1px_8px_rgba(10,10,10,0.06)]"
        aria-live="polite"
        aria-busy
      >
        <span className="flex gap-1" aria-hidden>
          <span className="h-2 w-2 animate-pulse rounded-full bg-[#C9A96E]/80" />
          <span className="h-2 w-2 animate-pulse rounded-full bg-[#C9A96E]/60 [animation-delay:150ms]" />
          <span className="h-2 w-2 animate-pulse rounded-full bg-[#C9A96E]/40 [animation-delay:300ms]" />
        </span>
        <span className="sr-only">{label}</span>
      </div>
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

  const [input, setInput] = useState('');
  const [preferredName, setPreferredName] = useState('');
  const [gender, setGender] = useState<'male' | 'female' | null>(null);
  const [topicId, setTopicId] = useState<TopicId | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [bootLoading, setBootLoading] = useState(true);
  const [turnLoading, setTurnLoading] = useState(false);
  const [streamHasContent, setStreamHasContent] = useState(false);
  const [intakeComplete, setIntakeComplete] = useState(false);
  const [intakeError, setIntakeError] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const [bootKey, setBootKey] = useState(0);

  const filledStep = [preferredName.trim(), gender, topicId].filter(Boolean).length;

  const applyExtracted = useCallback(
    async (res: {
      display_name?: string | null;
      gender?: 'male' | 'female' | null;
      topic?: string | null;
      intake_complete: boolean;
    }) => {
      const name = res.display_name?.trim();
      if (name) {
        const short = name.slice(0, 80);
        setPreferredName(short);
        try {
          await apiClient.updateProfile({ display_name: short });
          onDisplayNameUpdated?.(short);
        } catch {
          /* best-effort */
        }
      }
      if (res.gender === 'male' || res.gender === 'female') {
        setGender(res.gender);
        try {
          await apiClient.updateProfile({ gender: res.gender });
        } catch {
          /* best-effort */
        }
      }
      if (res.topic && isTopicId(res.topic)) setTopicId(res.topic);
      setIntakeComplete(res.intake_complete);
    },
    [onDisplayNameUpdated],
  );

  const buildKnownSlotsPayload = useCallback(
    (
      hint?: Partial<{
        gender: GenderId;
        topic: TopicId;
      }>,
      extras?: { display_name?: string },
    ): OnboardingKnownSlots | undefined => {
      const extraName = extras?.display_name?.trim();
      /** Never send profile/Clerk seed as display_name — it breaks intake (wrong glyphs, repeats wrong name). */
      const name = (extraName ? extraName.slice(0, 80) : '') || preferredName.trim();
      const g = hint?.gender ?? gender ?? undefined;
      const topic = hint?.topic ?? topicId ?? undefined;
      const out: OnboardingKnownSlots = {};
      if (name) out.display_name = name.slice(0, 80);
      if (g) out.gender = g;
      if (topic) out.topic = topic;
      return Object.keys(out).length ? out : undefined;
    },
    [preferredName, gender, topicId],
  );

  /** Static opening: same voice as workspace welcome, ends with “what’s your name?” — not the coaching-permission question. */
  useEffect(() => {
    let cancelled = false;
    setBootLoading(true);
    setStreamHasContent(true);
    setIntakeError(null);
    try {
      const text = buildIntakeOpeningMessage(null, null, i18n.language, t);
      if (!cancelled) {
        setMessages([{ id: uid(), role: 'coach', text }]);
      }
    } finally {
      if (!cancelled) setBootLoading(false);
    }
    return () => {
      cancelled = true;
    };
  }, [bootKey, i18n.language, t]);

  /** Keep opening copy in sync if user switches language before replying. */
  useEffect(() => {
    setMessages((prev) => {
      if (prev.length !== 1 || prev[0].role !== 'coach') return prev;
      const next = buildIntakeOpeningMessage(null, null, i18n.language, t);
      if (prev[0].text === next) return prev;
      return [{ ...prev[0], text: next }];
    });
  }, [i18n.language, t]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, bootLoading, turnLoading, intakeComplete, streamHasContent]);

  const coachLabel = t('bsdOnboarding.coachLabel');

  const sendUserTurn = useCallback(
    async (
      textOverride?: string,
      slotHint?: Partial<{
        gender: GenderId;
        topic: TopicId;
      }>,
    ) => {
      const raw = (textOverride ?? input).trim();
      if (!raw || bootLoading || turnLoading || intakeComplete) return;

      if (!textOverride) setInput('');
      setTurnLoading(true);
      setStreamHasContent(false);
      setIntakeError(null);

      let historySnapshot: ChatMsg[] = [];
      setMessages((prev) => {
        const userMsg: ChatMsg = { id: uid(), role: 'user', text: raw };
        historySnapshot = [...prev, userMsg];
        return historySnapshot;
      });

      let coachId: string | null = null;
      let buf = '';

      try {
        const apiMsgs = transcriptForApi(historySnapshot);
        const hintUsed = Boolean(slotHint && Object.keys(slotHint).length > 0);
        const nameForSlots = displayNameForKnownSlotsPayload(historySnapshot, raw, hintUsed);

        if (nameForSlots) {
          setPreferredName(nameForSlots.slice(0, 80));
        }

        const res = await apiClient.onboardingIntakeStream(
          {
            language: i18n.language,
            messages: apiMsgs,
            known_slots: buildKnownSlotsPayload(
              slotHint,
              nameForSlots ? { display_name: nameForSlots } : undefined,
            ),
          },
          {
            onToken: (d) => {
              buf += d;
              setStreamHasContent(true);
              if (!coachId) {
                coachId = uid();
                setMessages((prev) => [
                  ...prev,
                  {
                    id: coachId!,
                    role: 'coach',
                    text: buf,
                    showCoachMeta: true,
                  },
                ]);
              } else {
                setMessages((prev) =>
                  prev.map((m) => (m.id === coachId ? { ...m, text: buf } : m)),
                );
              }
            },
          },
        );

        if (coachId && res.assistant_message && buf !== res.assistant_message) {
          setMessages((prev) =>
            prev.map((m) => (m.id === coachId ? { ...m, text: res.assistant_message } : m)),
          );
        }
        await applyExtracted(res);
      } catch {
        setIntakeError(t('bsdOnboarding.intakeError'));
        if (!textOverride) setInput(raw);
        setMessages((prev) =>
          prev.length && prev[prev.length - 1]?.role === 'user' ? prev.slice(0, -1) : prev,
        );
      } finally {
        setTurnLoading(false);
      }
    },
    [
      applyExtracted,
      bootLoading,
      buildKnownSlotsPayload,
      input,
      intakeComplete,
      i18n.language,
      t,
      turnLoading,
    ],
  );

  const enterWorkspace = useCallback(async () => {
    try {
      await apiClient.patchUserPreferences({
        bsd_intro_screens_completed: true,
        bsd_onboard_topic: topicId ?? undefined,
      });
    } catch {
      /* App.tsx retries completion */
    }
    onComplete();
  }, [onComplete, topicId]);

  const showComposer = !intakeComplete;
  const composerBusy = bootLoading || turnLoading;
  const summaryReady =
    intakeComplete && preferredName.trim() && gender && topicId;
  const showTyping = composerBusy && !streamHasContent;
  const showQuickCards = !intakeComplete && !composerBusy;
  /** Opening asks for name first; gender cards are step 2 only after at least one user reply. */
  const hasUserMessaged = messages.some((m) => m.role === 'user');
  const showGenderPick = hasUserMessaged && !gender;
  const showTopicPick = Boolean(gender && !topicId);
  const showAnyQuickPick = showGenderPick || showTopicPick;

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

      <header
        className="relative z-[101] flex min-h-[66px] shrink-0 items-center justify-end border-b border-white/[0.07] bg-[#1e293b] px-4 py-4 shadow-[0_4px_18px_-2px_rgba(0,0,0,0.35)] backdrop-blur-[25px] md:justify-between md:px-6"
        dir="ltr"
      >
        <div className="hidden flex-1 md:block" aria-hidden />
        <div className="flex flex-shrink-0 items-center gap-3 md:gap-4">
          <div className="flex flex-col items-end gap-[7px]">
            <span
              className="text-[12px] text-white/[0.55] md:text-[14px]"
              style={{ fontFamily: 'Inter, sans-serif' }}
            >
              {t('bsdOnboarding.step', { current: Math.max(1, filledStep), total: STEPS })}
            </span>
            <div
              className="flex gap-[6px]"
              role="progressbar"
              aria-valuenow={filledStep}
              aria-valuemin={0}
              aria-valuemax={STEPS}
              aria-label={t('bsdOnboarding.step', { current: Math.max(1, filledStep), total: STEPS })}
            >
              {Array.from({ length: STEPS }, (_, i) => (
                <span
                  key={i}
                  className={cx(
                    'h-[3px] w-4 rounded-[50px] md:w-5',
                    i < filledStep ? 'bg-[#C8953A]' : 'bg-[#424345]',
                  )}
                />
              ))}
            </div>
          </div>
          <LanguageSwitcher variant="dark" />
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <LeftDecorPanel
          headlineBefore={t('bsdOnboarding.headlineBefore')}
          headlineAccent={t('bsdOnboarding.headlineAccent')}
          subtitle={t('bsdOnboarding.leftSubtitle')}
        />

        <section
          className="flex min-h-0 min-w-0 flex-1 flex-col bg-[#FAF8F3]"
          aria-label={t('bsdOnboarding.chatSection')}
        >
          <div
            ref={scrollRef}
            className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-4 md:px-12 md:py-6"
          >
            {intakeError && messages.length === 0 && !bootLoading ? (
              <div className="flex flex-col items-center gap-3 py-6 md:items-start">
                <p className="text-center text-[14px] text-red-700 md:text-start">{intakeError}</p>
                <button
                  type="button"
                  onClick={() => setBootKey((k) => k + 1)}
                  className="rounded-[11px] bg-[#1E293B] px-4 py-2 text-[14px] font-medium text-white"
                  style={{ fontFamily: 'Inter, sans-serif' }}
                >
                  {t('bsdOnboarding.retry')}
                </button>
              </div>
            ) : null}

            {intakeError && messages.length > 0 ? (
              <p className="text-center text-[14px] text-red-700 md:text-start">{intakeError}</p>
            ) : null}

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
                    {msg.showCoachMeta !== false ? <CoachRow label={coachLabel} /> : null}
                    <ChatBubble role="coach">{msg.text}</ChatBubble>
                  </>
                ) : (
                  <ChatBubble role="user">{msg.text}</ChatBubble>
                )}
              </div>
            ))}

            {showTyping ? <TypingIndicator label={t('bsdOnboarding.thinking')} /> : null}

            {showQuickCards ? (
              <div className="flex w-full flex-col gap-4 pb-2">
                {showAnyQuickPick ? (
                  <p
                    className="text-center text-[13px] text-[#4c5a70]/90 md:text-start"
                    style={{ fontFamily: 'Inter, sans-serif' }}
                  >
                    {t('bsdOnboarding.quickPickHint')}
                  </p>
                ) : null}

                {showGenderPick ? (
                  <div className="flex w-full justify-center md:justify-start">
                    <div className="grid w-full max-w-[432px] grid-cols-2 gap-3">
                      {GENDER_IDS.map((id) => (
                        <ChoiceCard
                          key={id}
                          icon={GENDER_ICONS[id]}
                          label={t(`bsdOnboarding.gender.${id}`)}
                          selected={false}
                          disabled={false}
                          onClick={() => void sendUserTurn(t(`bsdOnboarding.gender.${id}`), { gender: id })}
                        />
                      ))}
                    </div>
                  </div>
                ) : null}

                {showTopicPick ? (
                  <div className="flex w-full justify-center md:justify-start">
                    <div className="grid w-full max-w-[min(720px,100%)] grid-cols-3 gap-2 sm:gap-3">
                      {TOPIC_IDS.map((id) => (
                        <ChoiceCard
                          key={id}
                          icon={TOPIC_ICONS[id]}
                          label={t(`bsdOnboarding.topic.${id}`)}
                          selected={false}
                          disabled={false}
                          onClick={() => void sendUserTurn(t(`bsdOnboarding.topic.${id}`), { topic: id })}
                        />
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}

            {summaryReady ? (
              <div className="flex w-full flex-col items-center gap-5 pb-6 md:items-start">
                <div className="w-full max-w-[432px] rounded-2xl border border-[#E8E0CC] bg-white p-6 shadow-[0px_1px_8px_rgba(10,10,10,0.06)]">
                  <h3
                    className="text-lg font-medium text-[#1a1510]"
                    style={{ fontFamily: '"Cormorant Garamond", Georgia, serif' }}
                  >
                    {t('bsdOnboarding.summaryTitle')}
                  </h3>
                  <p className="mt-1 text-[14px] text-[#393939]/80">
                    {t('bsdOnboarding.summarySubtitle', {
                      name: preferredName || t('bsdOnboarding.fallbackName'),
                    })}
                  </p>
                  <dl className="mt-4 space-y-3 text-[14px]">
                    <div className="flex justify-between gap-4 border-b border-[#E8E0CC]/80 pb-2">
                      <dt className="text-[#4c5a70]">{t('bsdOnboarding.summary.name')}</dt>
                      <dd className="text-end font-medium text-[#1a1510]">{preferredName}</dd>
                    </div>
                    <div className="flex justify-between gap-4 border-b border-[#E8E0CC]/80 pb-2">
                      <dt className="text-[#4c5a70]">{t('bsdOnboarding.summary.gender')}</dt>
                      <dd className="text-end font-medium text-[#1a1510]">
                        {gender ? t(`bsdOnboarding.gender.${gender}`) : '—'}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-[#4c5a70]">{t('bsdOnboarding.summary.topic')}</dt>
                      <dd className="text-end font-medium text-[#1a1510]">
                        {topicId ? t(`bsdOnboarding.topic.${topicId}`) : '—'}
                      </dd>
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
            ) : null}
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
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      void sendUserTurn();
                    }
                  }}
                  disabled={composerBusy}
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
                  onClick={() => void sendUserTurn()}
                  disabled={composerBusy || !input.trim()}
                  className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-[7px] bg-[#1E293B] disabled:opacity-40"
                  aria-label={t('bsdOnboarding.sendAria')}
                >
                  <Send className="h-[13px] w-[13px] text-white" strokeWidth={2} />
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
