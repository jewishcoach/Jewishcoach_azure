import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@clerk/clerk-react';
import axios from 'axios';
import {
  Briefcase,
  Heart,
  Loader2,
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
import { apiClient, type OnboardingKnownSlots, runWithClerkToken } from '../services/api';
import {
  buildAfterGenderCoachMessage,
  buildAfterNameCoachMessage,
  getIntakeOpeningBlocks,
} from '../utils/welcomeMessage';

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

const DISPLAY_NAME_REFUSAL_NORMALIZED = new Set([
  'לא רוצה להגיד',
  'לא רוצה לומר',
  'לא רוצה לומר שם',
  'לא מעוניין לומר',
  'לא מעוניינת לומר',
  'עדיף לא לומר',
  'בלי שם',
  'אין לי שם',
  'לא חשוב',
  'סודי',
  'אנונימי',
  'prefer not to say',
  'rather not say',
  'no name',
  'anonymous',
  'skip',
]);

function normalizePhraseForRefusal(text: string): string {
  return stripIntakeNoise(text)
    .replace(/(?:[.!?…,:;"'`])+$/u, '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ');
}

/** User declines to share a name — do not treat as display_name. */
function isDisplayNameRefusalRaw(text: string): boolean {
  const c = normalizePhraseForRefusal(text);
  if (!c) return false;
  if (DISPLAY_NAME_REFUSAL_NORMALIZED.has(c)) return true;
  if (
    c === 'לא רוצה' ||
    c === 'לא מעוניין' ||
    c === 'לא מעוניינת' ||
    c === 'לא רוצה שם' ||
    c === 'בלי שם בבקשה'
  ) {
    return true;
  }
  if (c.includes('לא רוצה') && (c.includes('להגיד') || c.includes('לומר'))) return true;
  return false;
}

/** Gender decline / chip text — must never become display_name (e.g. «לא רוצה לשתף» is 3 tokens). */
function isGenderSkipLine(text: string): boolean {
  const c = normalizePhraseForRefusal(text);
  if (!c) return false;
  if (
    c === 'prefer not to say' ||
    c === 'prefer not to share' ||
    c === 'rather not say' ||
    c === "don't want to share" ||
    c === 'לא רוצה לשתף' ||
    c === 'לא רוצה לומר' ||
    c === 'לא משתף מגדר' ||
    c === 'לא רוצה לשתף מגדר' ||
    c === 'בלי מגדר' ||
    c === 'עדיף לא לומר'
  ) {
    return true;
  }
  if (
    c.includes('prefer not') ||
    c.includes('rather not') ||
    c.includes('skip gender') ||
    c.includes('no gender')
  ) {
    return true;
  }
  const needlesHe = [
    'לא רוצה לשתף',
    'לא רוצה לומר',
    'לא משתף',
    'בלי מגדר',
    'לא רלוונטי למגדר',
    'מגדר שלי',
  ];
  if (needlesHe.some((n) => c.includes(n))) return true;
  return false;
}

function isGenderSelectionLine(text: string): boolean {
  const t = stripIntakeNoise(text).replace(/(?:[.!?…,:;"'`])+\s*$/u, '').trim();
  if (!t) return false;
  if (isGenderSkipLine(t)) return true;
  const low = t.toLowerCase();
  if (low === 'male' || low === 'female' || low === 'm' || low === 'f') return true;
  if (low.includes("i'm male") || low.includes('i am male')) return true;
  if (low.includes("i'm female") || low.includes('i am female')) return true;
  if (t.includes('אני גבר') || t.includes('אני זכר')) return true;
  if (t.includes('אני אישה') || t.includes('אני אשה') || t.includes('אני נקבה')) return true;
  const compact = t.replace(/\s+/g, ' ').trim();
  const maleHe = new Set(['זכר', 'גבר', 'בן']);
  const femaleHe = new Set(['נקבה', 'אישה', 'אשה', 'בת']);
  return maleHe.has(compact) || femaleHe.has(compact) || maleHe.has(low) || femaleHe.has(low);
}

function guessDisplayNameFromFirstReply(text: string): string | undefined {
  const trimmed = stripIntakeNoise(text).replace(/(?:[.!?…])+$/u, '').trim();
  const t = trimmed;
  if (isDisplayNameRefusalRaw(t) || isGenderSkipLine(t)) return undefined;
  if (t.length < 2 || t.length > 48) return undefined;
  if (/[\n\r]/.test(t)) return undefined;
  if (/\d/.test(t)) return undefined;
  const words = t.split(/\s+/).filter(Boolean);
  if (words.length === 0 || words.length > 2) return undefined;
  const joined = words.join(' ');
  if (joined.length > 28) return undefined;
  const low = t.toLowerCase();
  if (
    low === 'זכר' ||
    low === 'נקבה' ||
    low === 'גבר' ||
    low === 'אישה' ||
    low === 'אשה' ||
    low === 'בן' ||
    low === 'בת' ||
    low === 'male' ||
    low === 'female' ||
    low === 'm' ||
    low === 'f'
  ) {
    return undefined;
  }
  if (!/^[\p{L}\s\-'.]+$/u.test(t)) return undefined;
  return joined.slice(0, 80);
}

/** When strict guess fails (e.g. 3-word name), still send a single-line reply as display_name on turn 1. */
function looseNameFromFirstReply(text: string): string | undefined {
  const t = stripIntakeNoise(text).replace(/(?:[.!?…])+$/u, '').trim();
  if (isDisplayNameRefusalRaw(t) || isGenderSkipLine(t)) return undefined;
  if (t.length < 2 || t.length > 48 || /[\n\r]/.test(t) || /\d/.test(t)) return undefined;
  const low = t.toLowerCase();
  if (
    low === 'זכר' ||
    low === 'נקבה' ||
    low === 'גבר' ||
    low === 'אישה' ||
    low === 'אשה' ||
    low === 'בן' ||
    low === 'בת' ||
    low === 'male' ||
    low === 'female' ||
    low === 'm' ||
    low === 'f'
  ) {
    return undefined;
  }
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
    if (isDisplayNameRefusalRaw(stripped) || isGenderSkipLine(stripped)) continue;
    const low = stripped.toLowerCase();
    if (
      low === 'זכר' ||
      low === 'נקבה' ||
      low === 'גבר' ||
      low === 'אישה' ||
      low === 'אשה' ||
      low === 'בן' ||
      low === 'בת' ||
      low === 'male' ||
      low === 'female' ||
      low === 'm' ||
      low === 'f'
    ) {
      continue;
    }
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
        style={{ fontFamily: WORKSPACE_CHAT_FONT }}
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
  compact = false,
}: {
  icon: LucideIcon;
  label: string;
  selected?: boolean;
  onClick: () => void;
  disabled?: boolean;
  /** Narrow 3-column topic grid on mobile — icon stays pinned above wrapped label */
  compact?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cx(
        'flex w-full min-w-0 flex-col items-center rounded-[18px] border bg-white text-center shadow-[0px_1px_8px_rgba(10,10,10,0.06)] transition-colors',
        compact
          ? 'min-h-[96px] justify-start gap-1.5 px-1.5 pb-2.5 pt-2.5 sm:min-h-[107px] sm:gap-2 sm:px-2 sm:pb-3 sm:pt-3'
          : 'h-[107px] justify-center gap-1 px-2 py-3 sm:px-3',
        selected
          ? 'border-[#C8953A] shadow-[0px_1px_28px_rgba(212,160,23,0.2)]'
          : 'border-[#E8E0CC] hover:border-[#d4c4a8]',
        disabled && 'pointer-events-none opacity-60',
      )}
      style={{ fontFamily: WORKSPACE_CHAT_FONT }}
    >
      <Icon
        className={cx(
          'shrink-0',
          compact ? 'h-6 w-6 sm:h-7 sm:w-7' : 'h-8 w-8',
          selected ? 'text-[#C8953A]' : 'text-[#6b7280]',
        )}
        strokeWidth={1.35}
      />
      <span
        className={cx(
          'font-medium text-[#393939]',
          compact
            ? 'text-[11px] leading-[1.25] sm:text-[12px] sm:leading-snug'
            : 'text-[14px] leading-snug',
        )}
      >
        {label}
      </span>
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
            style={{ fontFamily: WORKSPACE_CHAT_FONT }}
          >
            {subtitle}
          </p>
        </div>
      </div>
    </div>
  );
}

function CoachBubbleBody({ text }: { text: string }) {
  const blocks = text.split(/\n\n/).map((p) => p.trim()).filter(Boolean);
  return (
    <div className="flex flex-col gap-3">
      {blocks.map((block, i) => (
        <p key={i} className="m-0 whitespace-pre-wrap">
          {block}
        </p>
      ))}
    </div>
  );
}

const OPENING_BLOCK_PAUSE_MS = 420;
const OPENING_CHAR_MS = 26;
const OPENING_CHARS_PER_TICK = 2;

function sleep(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve) => {
    if (signal.aborted) {
      resolve();
      return;
    }
    const id = window.setTimeout(() => resolve(), ms);
    signal.addEventListener(
      'abort',
      () => {
        window.clearTimeout(id);
        resolve();
      },
      { once: true },
    );
  });
}

async function revealTypedBlock(
  fullText: string,
  onPartial: (partial: string) => void,
  signal: AbortSignal,
) {
  for (let i = 0; i < fullText.length; i += OPENING_CHARS_PER_TICK) {
    if (signal.aborted) return;
    onPartial(fullText.slice(0, Math.min(i + OPENING_CHARS_PER_TICK, fullText.length)));
    await sleep(OPENING_CHAR_MS, signal);
  }
  onPartial(fullText);
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
        'max-w-[min(497px,92vw)] rounded-[4px_18px_18px_18px] border border-[#E8E0CC] bg-white px-6 py-4 text-[14px] shadow-[0px_1px_8px_rgba(10,10,10,0.06)] md:text-[16px]',
        coach ? 'text-[#393939]' : 'text-[#1a1510]',
      )}
      style={{
        fontFamily: WORKSPACE_CHAT_FONT,
        fontWeight: 400,
        lineHeight: 1.65,
      }}
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
  const { getToken } = useAuth();
  const titleId = useId();
  const isHe = i18n.language.startsWith('he');
  const dir: 'rtl' | 'ltr' = isHe ? 'rtl' : 'ltr';

  const [input, setInput] = useState('');
  const [preferredName, setPreferredName] = useState('');
  const [gender, setGender] = useState<'male' | 'female' | null>(null);
  const [genderSkipped, setGenderSkipped] = useState(false);
  const [topicIds, setTopicIds] = useState<TopicId[]>([]);
  const [topicsSkipped, setTopicsSkipped] = useState(false);
  /** Local multi-select before confirming with the server */
  const [draftTopicIds, setDraftTopicIds] = useState<TopicId[]>([]);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [bootLoading, setBootLoading] = useState(true);
  const [openingBusy, setOpeningBusy] = useState(true);
  const [openingTypingText, setOpeningTypingText] = useState<string | null>(null);
  const [turnLoading, setTurnLoading] = useState(false);
  const [intakeComplete, setIntakeComplete] = useState(false);
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [enteringWorkspace, setEnteringWorkspace] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const openingLangRef = useRef(i18n.language);
  const [bootKey, setBootKey] = useState(0);

  useEffect(() => {
    apiClient.bindClerkAuth(getToken);
  }, [getToken]);

  /** Refresh JWT when opening finishes — user often reads 1–2 min before typing their name. */
  useEffect(() => {
    if (openingBusy || bootLoading) return;
    void (async () => {
      const token = await getToken({ skipCache: true });
      if (token) apiClient.setToken(token);
    })();
  }, [openingBusy, bootLoading, getToken]);

  const genderStepDone = Boolean(gender || genderSkipped);
  const prevGenderStepDoneRef = useRef(false);
  useEffect(() => {
    if (genderStepDone && !prevGenderStepDoneRef.current) {
      setDraftTopicIds([]);
    }
    prevGenderStepDoneRef.current = genderStepDone;
  }, [genderStepDone]);

  const namePhaseDone =
    Boolean(preferredName.trim()) ||
    messages.some((m) => m.role === 'user' && isDisplayNameRefusalRaw(m.text));
  const topicMilestoneDone = topicsSkipped || topicIds.length > 0;
  const filledStep = [namePhaseDone, genderStepDone, topicMilestoneDone].filter(Boolean).length;

  const applyExtracted = useCallback(
    async (res: {
      display_name?: string | null;
      gender?: 'male' | 'female' | null;
      topic?: string | null;
      topics?: string[] | null;
      topics_skipped?: boolean;
      gender_skipped?: boolean;
      intake_complete: boolean;
    }) => {
      const name = res.display_name?.trim();
      if (name && !isDisplayNameRefusalRaw(name)) {
        const short = name.slice(0, 80);
        setPreferredName(short);
        void (async () => {
          try {
            await runWithClerkToken(getToken, () =>
              apiClient.updateProfile({ display_name: short }),
            );
            onDisplayNameUpdated?.(short);
          } catch {
            /* best-effort */
          }
        })();
      }
      const effectiveGender: 'male' | 'female' | null =
        res.gender === 'male' || res.gender === 'female' ? res.gender : null;
      if (res.gender_skipped === true) {
        setGenderSkipped(true);
        setGender(null);
      } else if (effectiveGender === 'male' || effectiveGender === 'female') {
        setGenderSkipped(false);
        setGender(effectiveGender);
        void (async () => {
          try {
            await runWithClerkToken(getToken, () =>
              apiClient.updateProfile({ gender: effectiveGender }),
            );
          } catch {
            /* best-effort */
          }
        })();
      }

      if (res.topics_skipped) {
        setTopicsSkipped(true);
        setTopicIds([]);
        setDraftTopicIds([]);
      } else {
        setTopicsSkipped(false);
        const fromApi = (res.topics ?? []).filter(isTopicId);
        const next =
          fromApi.length > 0
            ? fromApi
            : res.topic && isTopicId(res.topic)
              ? [res.topic]
              : [];
        setTopicIds(next);
        setDraftTopicIds(next);
      }
      setIntakeComplete(res.intake_complete);
    },
    [onDisplayNameUpdated, getToken],
  );

  const buildKnownSlotsPayload = useCallback(
    (
      hint?: Partial<{
        gender: GenderId;
        genderSkipped: boolean;
        topic: TopicId;
        topics: TopicId[];
        topicsSkipped: boolean;
      }>,
      extras?: { display_name?: string },
    ): OnboardingKnownSlots | undefined => {
      const extraName = extras?.display_name?.trim();
      /** Never send profile/Clerk seed as display_name — it breaks intake (wrong glyphs, repeats wrong name). */
      const name = (extraName ? extraName.slice(0, 80) : '') || preferredName.trim();
      const out: OnboardingKnownSlots = {};
      if (name) out.display_name = name.slice(0, 80);

      if (hint?.genderSkipped === true) {
        out.gender_skipped = true;
      } else if (hint?.gender === 'male' || hint?.gender === 'female') {
        out.gender = hint.gender;
      } else if (gender === 'male' || gender === 'female') {
        out.gender = gender;
      } else if (genderSkipped) {
        out.gender_skipped = true;
      }

      if (hint?.topicsSkipped === true) {
        out.topics_skipped = true;
      } else {
        const hintedTopics = hint?.topics?.filter(isTopicId);
        if (hintedTopics && hintedTopics.length > 0) {
          out.topics = hintedTopics;
        } else if (hint?.topic && isTopicId(hint.topic)) {
          out.topic = hint.topic;
        } else if (
          !hint?.gender &&
          !hint?.genderSkipped &&
          topicIds.length > 0 &&
          !topicsSkipped
        ) {
          out.topics = [...topicIds];
        }
      }

      return Object.keys(out).length ? out : undefined;
    },
    [preferredName, gender, genderSkipped, topicIds, topicsSkipped],
  );

  const toggleDraftTopic = useCallback((id: TopicId) => {
    setDraftTopicIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }, []);

  /** Opening: three coach bubbles, typed in sequence (no API). */
  useEffect(() => {
    const ac = new AbortController();
    let cancelled = false;

    const run = async () => {
      setBootLoading(true);
      setOpeningBusy(true);
      setIntakeError(null);
      setMessages([]);
      setOpeningTypingText(null);

      const blocks = getIntakeOpeningBlocks(i18n.language, t);
      try {
        for (let bi = 0; bi < blocks.length; bi += 1) {
          if (ac.signal.aborted || cancelled) return;
          setOpeningTypingText('');
          await revealTypedBlock(
            blocks[bi],
            (partial) => {
              if (!cancelled) setOpeningTypingText(partial);
            },
            ac.signal,
          );
          if (ac.signal.aborted || cancelled) return;
          setMessages((prev) => [
            ...prev,
            {
              id: uid(),
              role: 'coach',
              text: blocks[bi],
              showCoachMeta: bi === 0,
            },
          ]);
          setOpeningTypingText(null);
          if (bi < blocks.length - 1) {
            await sleep(OPENING_BLOCK_PAUSE_MS, ac.signal);
          }
        }
      } finally {
        if (!cancelled) {
          setBootLoading(false);
          setOpeningBusy(false);
          setOpeningTypingText(null);
        }
      }
    };

    void run();
    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [bootKey, i18n.language, t]);

  useEffect(() => {
    void apiClient.warmupCache(i18n.language);
  }, [i18n.language]);

  /** Restart opening sequence if language changes before the user replies. */
  useEffect(() => {
    if (openingLangRef.current === i18n.language) return;
    openingLangRef.current = i18n.language;
    if (messages.some((m) => m.role === 'user')) return;
    setBootKey((k) => k + 1);
  }, [i18n.language, messages]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, bootLoading, turnLoading, intakeComplete, openingTypingText]);

  const coachLabel = t('bsdOnboarding.coachLabel');

  const sendUserTurn = useCallback(
    async (
      textOverride?: string,
      slotHint?: Partial<{
        gender: GenderId;
        genderSkipped: boolean;
        topic: TopicId;
        topics: TopicId[];
        topicsSkipped: boolean;
      }>,
    ) => {
      const raw = (textOverride ?? input).trim();
      if (!raw || bootLoading || openingBusy || turnLoading || intakeComplete) return;

      if (!textOverride) setInput('');
      setTurnLoading(true);
      setIntakeError(null);

      const rollbackGender = gender;
      const rollbackGenderSkipped = genderSkipped;
      const rollbackTopicIds = topicIds;
      const rollbackTopicsSkipped = topicsSkipped;
      const rollbackDraftTopicIds = draftTopicIds;

      let historySnapshot: ChatMsg[] = [];
      setMessages((prev) => {
        const userMsg: ChatMsg = { id: uid(), role: 'user', text: raw };
        historySnapshot = [...prev, userMsg];
        return historySnapshot;
      });

      try {
        if (slotHint?.genderSkipped === true) {
          setGenderSkipped(true);
          setGender(null);
        }
        if (slotHint?.gender === 'male' || slotHint?.gender === 'female') {
          setGender(slotHint.gender);
          setGenderSkipped(false);
        }

        const apiMsgs = transcriptForApi(historySnapshot);
        const hintUsed = Boolean(slotHint && Object.keys(slotHint).length > 0);
        const nameForSlots = displayNameForKnownSlotsPayload(historySnapshot, raw, hintUsed);

        const resolvedName =
          nameForSlots && !isDisplayNameRefusalRaw(nameForSlots)
            ? nameForSlots.slice(0, 80)
            : undefined;
        if (resolvedName) {
          setPreferredName(resolvedName);
        }

        const isFirstNameReply =
          !hintUsed &&
          historySnapshot.filter((m) => m.role === 'user').length === 1 &&
          Boolean(resolvedName);

        const hadGenderBefore = Boolean(gender || genderSkipped);
        const acceptsGender =
          slotHint?.gender === 'male' ||
          slotHint?.gender === 'female' ||
          slotHint?.genderSkipped === true ||
          (!hintUsed && isGenderSelectionLine(raw));
        const isGenderToTopicReply =
          !hadGenderBefore &&
          acceptsGender &&
          (Boolean(preferredName.trim()) ||
            historySnapshot.some(
              (m) => m.role === 'user' && isDisplayNameRefusalRaw(m.text),
            ));

        let optimisticCoachId: string | undefined;
        if (isFirstNameReply && resolvedName) {
          const coachId = uid();
          optimisticCoachId = coachId;
          const optimisticText = buildAfterNameCoachMessage(resolvedName, i18n.language, t);
          setMessages((prev) => [
            ...prev,
            {
              id: coachId,
              role: 'coach',
              text: optimisticText,
              showCoachMeta: true,
            },
          ]);
        } else if (isGenderToTopicReply) {
          const coachId = uid();
          optimisticCoachId = coachId;
          const optimisticText = buildAfterGenderCoachMessage(i18n.language, t);
          setMessages((prev) => [
            ...prev,
            {
              id: coachId,
              role: 'coach',
              text: optimisticText,
              showCoachMeta: true,
            },
          ]);
        }

        const res = await runWithClerkToken(getToken, () =>
          apiClient.onboardingIntakeStep({
            language: i18n.language,
            messages: apiMsgs,
            known_slots: buildKnownSlotsPayload(
              slotHint,
              resolvedName ? { display_name: resolvedName } : undefined,
            ),
          }),
        );

        const serverText = res.assistant_message || '…';
        if (optimisticCoachId) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === optimisticCoachId ? { ...m, text: serverText } : m,
            ),
          );
        } else {
          setMessages((prev) => [
            ...prev,
            {
              id: uid(),
              role: 'coach',
              text: serverText,
              showCoachMeta: true,
            },
          ]);
        }
        void applyExtracted(res);
      } catch (err) {
        const authFailed =
          (err instanceof Error &&
            (err.message === 'no_auth' || err.message === 'auth_failed')) ||
          (axios.isAxiosError(err) && err.response?.status === 401);
        setIntakeError(
          authFailed ? t('bsdOnboarding.authError') : t('bsdOnboarding.intakeError'),
        );
        setGender(rollbackGender);
        setGenderSkipped(rollbackGenderSkipped);
        setTopicIds(rollbackTopicIds);
        setTopicsSkipped(rollbackTopicsSkipped);
        setDraftTopicIds(rollbackDraftTopicIds);
        if (!textOverride) setInput(raw);
        setMessages((prev) =>
          prev.length && prev[prev.length - 1]?.role === 'user' ? prev.slice(0, -1) : prev,
        );
      } finally {
        setTurnLoading(false);
      }
    },
    [
      getToken,
      applyExtracted,
      bootLoading,
      openingBusy,
      buildKnownSlotsPayload,
      draftTopicIds,
      gender,
      genderSkipped,
      input,
      intakeComplete,
      i18n.language,
      t,
      topicIds,
      topicsSkipped,
      turnLoading,
      preferredName,
      gender,
      genderSkipped,
    ],
  );

  const enterWorkspace = useCallback(async () => {
    if (enteringWorkspace) return;
    setEnteringWorkspace(true);
    try {
      const patch: Record<string, unknown> = {
        bsd_intro_screens_completed: true,
      };
      if (topicsSkipped) {
        patch.bsd_topics_skipped = true;
        patch.bsd_onboard_topics = [];
      } else {
        patch.bsd_onboard_topics = topicIds;
        if (topicIds[0]) patch.bsd_onboard_topic = topicIds[0];
      }
      await runWithClerkToken(getToken, () => apiClient.patchUserPreferences(patch));
    } catch {
      /* App.tsx retries completion */
    }
    onComplete();
  }, [enteringWorkspace, getToken, onComplete, topicIds, topicsSkipped]);

  const showComposer = !intakeComplete && !openingBusy;
  const composerBusy = bootLoading || openingBusy || turnLoading;
  const summaryReady = intakeComplete && genderStepDone && topicMilestoneDone;
  const awaitingCoachReply =
    turnLoading &&
    messages.length > 0 &&
    messages[messages.length - 1]?.role === 'user';
  const showTyping = awaitingCoachReply;
  const showQuickCards = !intakeComplete && !bootLoading && !openingBusy;
  /** Opening asks for name first; gender cards are step 2 only after at least one user reply. */
  const hasUserMessaged = messages.some((m) => m.role === 'user');
  const showGenderPick = hasUserMessaged && !gender && !genderSkipped;
  const showTopicPick = genderStepDone && !intakeComplete;

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
              style={{ fontFamily: WORKSPACE_CHAT_FONT }}
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
                  style={{ fontFamily: WORKSPACE_CHAT_FONT }}
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
                    <ChatBubble role="coach">
                      <CoachBubbleBody text={msg.text} />
                    </ChatBubble>
                  </>
                ) : (
                  <ChatBubble role="user">{msg.text}</ChatBubble>
                )}
              </div>
            ))}

            {openingTypingText !== null ? (
              <div className="flex w-full flex-col items-start gap-2">
                {messages.length === 0 ? <CoachRow label={coachLabel} /> : null}
                <ChatBubble role="coach">
                  <CoachBubbleBody text={openingTypingText} />
                </ChatBubble>
              </div>
            ) : null}

            {showTyping ? <TypingIndicator label={t('bsdOnboarding.thinking')} /> : null}

            {showQuickCards ? (
              <div className="flex w-full flex-col gap-4 pb-2">
                {showGenderPick ? (
                  <p
                    className="text-center text-[13px] text-[#4c5a70]/90 md:text-start"
                    style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                  >
                    {t('bsdOnboarding.quickPickHint')}
                  </p>
                ) : null}

                {showGenderPick ? (
                  <div className="flex w-full flex-col items-center gap-3 md:items-start">
                    <div className="grid w-full max-w-[432px] grid-cols-2 gap-3">
                      {GENDER_IDS.map((id) => (
                        <ChoiceCard
                          key={id}
                          icon={GENDER_ICONS[id]}
                          label={t(`bsdOnboarding.gender.${id}`)}
                          selected={false}
                          disabled={turnLoading}
                          onClick={() => void sendUserTurn(t(`bsdOnboarding.gender.${id}`), { gender: id })}
                        />
                      ))}
                    </div>
                    <button
                      type="button"
                      disabled={composerBusy}
                      onClick={() =>
                        void sendUserTurn(t('bsdOnboarding.genderSkippedLine'), { genderSkipped: true })
                      }
                      className="w-full max-w-[432px] rounded-[11px] border border-[#E8E0CC] bg-white px-4 py-3 text-[14px] font-medium text-[#393939] shadow-sm transition enabled:hover:bg-[#faf6ee] disabled:opacity-40"
                      style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                    >
                      {t('bsdOnboarding.genderSkip')}
                    </button>
                  </div>
                ) : null}

                {showTopicPick ? (
                  <div className="flex w-full flex-col items-center gap-4 md:items-start">
                    <div className="grid w-full max-w-[min(720px,100%)] grid-cols-3 gap-2 sm:gap-3">
                      {TOPIC_IDS.map((id) => (
                        <ChoiceCard
                          key={id}
                          icon={TOPIC_ICONS[id]}
                          label={t(`bsdOnboarding.topic.${id}`)}
                          selected={draftTopicIds.includes(id)}
                          disabled={false}
                          compact
                          onClick={() => toggleDraftTopic(id)}
                        />
                      ))}
                    </div>
                    <div className="flex w-full max-w-[min(720px,100%)] flex-col gap-2 sm:flex-row sm:items-center sm:justify-start sm:gap-3">
                      <button
                        type="button"
                        disabled={composerBusy || draftTopicIds.length === 0}
                        onClick={() =>
                          void sendUserTurn(
                            t('bsdOnboarding.topicContinueLine', {
                              topics: draftTopicIds
                                .map((tid) => t(`bsdOnboarding.topic.${tid}`))
                                .join(isHe ? ', ' : ', '),
                            }),
                            { topics: draftTopicIds },
                          )
                        }
                        className="w-full rounded-[11px] bg-[#1E293B] px-4 py-3 text-[14px] font-medium text-white shadow-sm transition enabled:hover:bg-[#151e2e] disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto sm:min-w-[200px]"
                        style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                      >
                        {t('bsdOnboarding.topicContinue')}
                      </button>
                      <button
                        type="button"
                        disabled={composerBusy}
                        onClick={() =>
                          void sendUserTurn(t('bsdOnboarding.topicSkippedLine'), { topicsSkipped: true })
                        }
                        className="w-full rounded-[11px] border border-[#E8E0CC] bg-white px-4 py-3 text-[14px] font-medium text-[#393939] shadow-sm transition enabled:hover:bg-[#faf6ee] disabled:opacity-40 sm:w-auto"
                        style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                      >
                        {t('bsdOnboarding.topicSkip')}
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}

            {summaryReady ? (
              <div className="flex w-full flex-col items-center gap-5 pb-6 md:items-start">
                <div className="w-full max-w-[432px] rounded-2xl border border-[#E8E0CC] bg-white p-6 shadow-[0px_1px_8px_rgba(10,10,10,0.06)]">
                  <h3
                    className="text-lg font-semibold text-[#1a1510]"
                    style={{ fontFamily: WORKSPACE_CHAT_FONT }}
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
                        {gender === 'male' || gender === 'female'
                          ? t(`bsdOnboarding.gender.${gender}`)
                          : genderSkipped
                            ? t('bsdOnboarding.summaryGenderSkipped')
                            : '—'}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-[#4c5a70]">{t('bsdOnboarding.summary.topic')}</dt>
                      <dd className="max-w-[min(240px,55%)] text-end font-medium text-[#1a1510]">
                        {topicsSkipped
                          ? t('bsdOnboarding.summaryTopicsSkipped')
                          : topicIds.length > 0
                            ? topicIds.map((tid) => t(`bsdOnboarding.topic.${tid}`)).join(' · ')
                            : '—'}
                      </dd>
                    </div>
                  </dl>
                  <div className="mt-5 border-t border-[#E8E0CC]/80 pt-4">
                    <h4
                      className="text-lg font-semibold text-[#1a1510]"
                      style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                    >
                      {t('bsdOnboarding.summaryPaceTitle')}
                    </h4>
                    <p className="mt-1 whitespace-pre-line text-[14px] text-[#393939]/80">
                      {t('bsdOnboarding.summaryPaceBody')}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  disabled={enteringWorkspace}
                  aria-busy={enteringWorkspace}
                  onClick={() => void enterWorkspace()}
                  className="flex w-full max-w-[432px] min-h-[48px] items-center justify-center rounded-[11px] bg-[#1E293B] py-3 text-[15px] font-medium text-white shadow-sm transition enabled:hover:bg-[#151e2e] disabled:cursor-wait disabled:opacity-95"
                  style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                >
                  {enteringWorkspace ? (
                    <span className="inline-flex items-center justify-center gap-2">
                      <Loader2 className="h-5 w-5 shrink-0 animate-spin" aria-hidden />
                      <span>{t('bsdOnboarding.enteringSpace')}</span>
                    </span>
                  ) : (
                    t('bsdOnboarding.enterSpace')
                  )}
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
                  style={{ fontFamily: WORKSPACE_CHAT_FONT }}
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
