/**
 * Vision Ladder - לפי חוברת "תהליך השיבה" מהדורה שלישית
 * שלבים כפי שמופיעים בחוברת
 * לחיצה על שלב – גלילה חכמה להודעה הראשונה באותו שלב
 * במובייל: שלבים עם תובנות מציגים אינדיקציה, לחיצה מציגה popover
 */

import { useState, useEffect, useRef, useId } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@clerk/clerk-react';
import { Check } from 'lucide-react';
import { apiClient } from '../../services/api';
import { buildInsightsByPhase, type InsightItem } from '../../utils/insightsByPhase';
import { WORKSPACE_CHAT_FONT } from '../../constants/workspaceFonts';

// מיפוי שלב נוכחי (S0-S15) → אינדקס שלב בחוברת
const STEP_TO_PHASE: Record<string, number> = {
  S0: 0,                                 // בקשה לאימון
  S1: 1, S2: 1, S3: 1, S4: 1, S5: 1,    // מצוי (נושא, אירוע, רגש, מחשבה, מעשה)
  S6: 2,                                 // רצוי
  S7: 3,                                 // פער
  S8: 4,                                 // דפוס
  S9: 5,                                 // פרדיגמה
  S10: 6, S11: 6,                       // עמדה+טריגר, רווחים
  S12: 8,                               // כמ"ז (מקור-טבע-שכל)
  S13: 9, S14: 10, S15: 10,             // בחירה, חזון ומחויבות
};

// 11 שלבים לפי החוברת (מקור-טבע-שכל וכמ"ז – אותו שלב) – תרגום ב-i18n
const PHASE_IDS = ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8', 'p9', 'p10'];

interface VisionLadderProps {
  currentStep: string;
  onPhaseClick?: (phaseIndex: number) => void;
  /** Compact strip for mobile - narrow vertical dots */
  compact?: boolean;
  /** For compact: fetch insights and show popover on tap */
  conversationId?: number | null;
}

/** Serif title per journey panel design */
const JOURNEY_TITLE_SERIF = "'Playfair Display', Georgia, 'Times New Roman', serif";

function JourneyProgressRing({ pct, fraction }: { pct: number; fraction: string }) {
  const gradId = useId().replace(/:/g, '');
  const r = 31;
  const c = 2 * Math.PI * r;
  const clamped = Math.min(100, Math.max(0, pct));
  const offset = c - (clamped / 100) * c;
  return (
    <div className="relative h-[76px] w-[76px] shrink-0" aria-hidden>
      <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(45,55,72,0.95)" strokeWidth="5" />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke={`url(#vision-ladder-ring-gold-${gradId})`}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
        <defs>
          <linearGradient id={`vision-ladder-ring-gold-${gradId}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#fcefb6" />
            <stop offset="45%" stopColor="#e8c066" />
            <stop offset="100%" stopColor="#b8892a" />
          </linearGradient>
        </defs>
      </svg>
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <span
          className="text-[14px] font-semibold tracking-tight text-white tabular-nums"
          style={{ fontFamily: JOURNEY_TITLE_SERIF }}
        >
          {fraction}
        </span>
      </div>
    </div>
  );
}

export const VisionLadder = ({
  currentStep,
  onPhaseClick,
  compact = false,
  conversationId,
}: VisionLadderProps) => {
  const { t, i18n } = useTranslation();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const activePhaseIndex = STEP_TO_PHASE[currentStep] ?? 0;
  const isRTL = i18n.language === 'he' || i18n.language?.startsWith('he');
  const [insightsByPhase, setInsightsByPhase] = useState<Record<number, InsightItem[]>>({});
  const [popoverPhase, setPopoverPhase] = useState<number | null>(null);
  /** Phase index that should play a one-shot border pulse (step transition only, not initial mount). */
  const [pulsePhaseIndex, setPulsePhaseIndex] = useState<number | null>(null);
  const prevPhaseIndexRef = useRef<number | null>(null);

  useEffect(() => {
    const prev = prevPhaseIndexRef.current;
    if (prev !== null && prev !== activePhaseIndex) {
      setPulsePhaseIndex(activePhaseIndex);
      // Match compact circle blink duration (~2.6s) + desktop step pulse
      const id = window.setTimeout(() => setPulsePhaseIndex(null), 2800);
      prevPhaseIndexRef.current = activePhaseIndex;
      return () => clearTimeout(id);
    }
    prevPhaseIndexRef.current = activePhaseIndex;
  }, [activePhaseIndex]);

  // Fetch insights when compact and conversationId available
  useEffect(() => {
    if (!compact || !conversationId) {
      setInsightsByPhase({});
      return;
    }
    if (!isLoaded || !isSignedIn) return;

    let interval: NodeJS.Timeout | null = null;
    const fetchData = async () => {
      try {
        const token = await getToken();
        if (token) apiClient.setToken(token);
        const res = await apiClient.getConversationInsights(conversationId);
        if (res.exists === false || !res.cognitive_data) return;
        const phase = res.current_stage ?? currentStep;
        const map = buildInsightsByPhase(res.cognitive_data, phase, t);
        setInsightsByPhase(map);
      } catch {
        setInsightsByPhase({});
      }
    };
    fetchData();
    interval = setInterval(fetchData, 3000);
    return () => { if (interval) clearInterval(interval); };
  }, [compact, conversationId, currentStep, t, isLoaded, isSignedIn, getToken]);

  if (compact) {
    return (
      <div
        className="box-border w-[84px] flex-shrink-0 flex h-full min-h-0 flex-col justify-between py-2 bg-[#1e293b] border-r border-white/[0.07] rtl:border-r-0 rtl:border-l rtl:border-l-white/[0.07] relative"
        dir={isRTL ? 'rtl' : 'ltr'}
      >
        {PHASE_IDS.map((phaseId, i) => {
          const isActive = i === activePhaseIndex;
          const isPast = i < activePhaseIndex;
          const hasInsight = (insightsByPhase[i]?.length ?? 0) > 0;
          const title = phaseId === 'p0' ? t('ladder.p0.compact') : t(`ladder.${phaseId}`);
          const scrollHint = t('ladder.scrollHint');
          const showPopover = popoverPhase === i;
          const insights = insightsByPhase[i] ?? [];
          const isCirclePulsing = isActive && pulsePhaseIndex === i;

          return (
            <div key={phaseId} className="relative flex flex-col items-center">
              <button
                type="button"
                onClick={() => {
                  onPhaseClick?.(i);
                  if (hasInsight) setPopoverPhase((p) => (p === i ? null : i));
                  else setPopoverPhase(null);
                }}
                title={`${title} - ${scrollHint}`}
                className="flex flex-col items-center gap-0.5 py-0.5 min-w-0 rounded-lg"
                aria-label={`${title} - ${scrollHint}`}
              >
                <span
                  className={`relative w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold flex-shrink-0 ${
                    isActive
                      ? 'bg-[#FCF6BA]/90 text-[#020617] ring-2 ring-[#B38728]/65'
                      : isPast
                        ? 'bg-white/35 text-white/[0.88] ring-1 ring-white/40'
                        : 'bg-white/20 text-white/60 ring-1 ring-white/22'
                  } ${isCirclePulsing ? 'vision-ladder-compact-circle-blink' : ''}`}
                >
                  {i + 1}
                  {hasInsight && (
                    <span
                      className="absolute -top-0.5 -end-0.5 w-2 h-2 rounded-full bg-[#FCF6BA]/90 ring-1 ring-[#1e293b]"
                      aria-hidden
                    />
                  )}
                </span>
                <span
                  className={`text-[10px] leading-tight text-center truncate max-w-full px-0.5 font-semibold ${
                    isActive ? 'text-[#FCF6BA]/95' : isPast ? 'text-white/[0.82]' : 'text-white/[0.58]'
                  }`}
                >
                  {title}
                </span>
              </button>
              {showPopover && hasInsight && insights.length > 0 && (
                <>
                  <div
                    className="fixed inset-0 z-[60]"
                    onClick={() => setPopoverPhase(null)}
                    aria-hidden
                  />
                  <div
                    className="fixed z-[70] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 min-w-[220px] max-w-[min(300px,90vw)] rounded-xl p-4 shadow-xl border"
                    style={{
                      background: 'rgba(2,6,23,0.98)',
                      borderColor: 'rgba(252,246,186,0.3)',
                      fontFamily: WORKSPACE_CHAT_FONT,
                    }}
                  >
                    <div className="space-y-2">
                      {insights.map((item, idx) => (
                        <div key={idx}>
                          <span className="text-[10px] uppercase tracking-wider text-[#FCF6BA]/80">{item.label}</span>
                          <p className="text-[12px] text-[#F5F5F0]/95 mt-0.5 break-words whitespace-pre-wrap" style={{ lineHeight: 1.45 }}>
                            {item.value}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  const totalStages = PHASE_IDS.length;
  const stageOrdinal = activePhaseIndex + 1;
  const progressPct = Math.min(
    100,
    Math.round((activePhaseIndex / Math.max(1, totalStages - 1)) * 100),
  );
  const activePhaseKey = PHASE_IDS[activePhaseIndex] ?? 'p0';

  return (
    <div
      className="workspace-ladder flex h-full min-w-0 w-full max-w-full flex-col overflow-x-hidden bg-[#1e293b]"
      dir={isRTL ? 'rtl' : 'ltr'}
    >
      {/* כותרת — שלבי האימון שלך + כרטיס התקדמות */}
      <header className="flex-shrink-0 overflow-x-hidden border-b border-white/[0.06] px-5 pb-4 pt-6">
        <h2
          className="text-[1.5rem] font-semibold leading-tight tracking-[0.02em] text-white sm:text-[1.65rem]"
          style={{ fontFamily: isRTL ? WORKSPACE_CHAT_FONT : JOURNEY_TITLE_SERIF }}
        >
          {t('ladder.journeyTitle')}
        </h2>

        <div className="mt-3 rounded-xl border border-white/[0.07] bg-[#252f3f] px-3 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
          <div className={`flex items-center gap-3 ${isRTL ? 'flex-row-reverse' : ''}`}>
            <JourneyProgressRing pct={progressPct} fraction={`${stageOrdinal}/${totalStages}`} />
            <div className="min-w-0 flex-1">
              <p
                className="text-[15px] font-bold leading-snug text-[#fcefb6]"
                style={{ fontFamily: WORKSPACE_CHAT_FONT }}
              >
                {t(`ladder.${activePhaseKey}`)}
              </p>
              <p className="mt-1.5 font-semibold text-[#e2e8f0] text-[12px] leading-snug" style={{ fontFamily: WORKSPACE_CHAT_FONT }}>
                {t('ladder.progressPct', { pct: progressPct })}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* סולם שלבים */}
      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-x-hidden px-5 pb-6 pt-3">
        <div
          className="pointer-events-none absolute bottom-6 top-4 w-px bg-gradient-to-b from-white/12 via-white/18 to-white/10"
          style={{ insetInlineStart: '2.625rem' }}
          aria-hidden
        />

        <div className="custom-scrollbar flex min-h-0 min-w-0 flex-1 flex-col gap-1 overflow-y-auto overflow-x-hidden pe-0.5">
          {PHASE_IDS.map((phaseId, i) => {
            const title = t(`ladder.${phaseId}`);
            const tagline = t(`ladder.${phaseId}.tagline`);
            const tooltip = t(`ladder.${phaseId}.tooltip`);
            const isActive = i === activePhaseIndex;
            const isPast = i < activePhaseIndex;
            const isClickable = !!onPhaseClick;
            const scrollHint = t('ladder.scrollHint');
            const isStepPulsing = isActive && pulsePhaseIndex === i;

            return (
              <div key={phaseId} className="group relative z-[1]">
                <div
                  role={isClickable ? 'button' : undefined}
                  tabIndex={isClickable ? 0 : undefined}
                  aria-label={isClickable ? `${title} - ${scrollHint}` : undefined}
                  onClick={isClickable ? () => onPhaseClick(i) : undefined}
                  onKeyDown={
                    isClickable
                      ? (e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            onPhaseClick(i);
                          }
                        }
                      : undefined
                  }
                  className={`relative flex w-full items-start gap-3 rounded-xl py-3 ps-1 pe-2 transition-colors duration-200 ${
                    isStepPulsing ? 'vision-ladder-desktop--step-pulse transition-none' : ''
                  } ${isClickable ? 'cursor-pointer hover:bg-white/[0.03]' : 'cursor-default'} ${
                    isActive
                      ? 'border border-[#d4af37]/35 bg-[rgba(212,175,55,0.09)] shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]'
                      : 'border border-transparent'
                  }`}
                >
                  {/* עמודת ציר — מרכוז האייקון על הקו */}
                  <div className="relative z-[2] flex w-9 flex-shrink-0 justify-center pt-0.5">
                    {isPast ? (
                      <span className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-[#e8c066] bg-[#1e293b] shadow-[0_0_0_1px_rgba(212,175,55,0.15)]">
                        <Check className="h-[18px] w-[18px] text-[#f4e4a8]" strokeWidth={2.75} aria-hidden />
                      </span>
                    ) : isActive ? (
                      <span
                        className="vision-ladder-active-node flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-[#fcefb6] via-[#e8c066] to-[#b8892a] text-[13px] font-bold tabular-nums text-[#1a2332] ring-2 ring-[#fcefb6]/35"
                      >
                        {i + 1}
                      </span>
                    ) : (
                      <span className="flex h-9 w-9 items-center justify-center rounded-full border border-white/28 bg-[#1e293b]/80 text-[12px] font-bold tabular-nums text-[#94a3b8]">
                        {i + 1}
                      </span>
                    )}
                  </div>

                  <div className="min-w-0 flex-1 pt-1">
                    <div
                      className={`text-[15px] font-bold leading-snug ${
                        isActive ? 'text-white' : isPast ? 'text-white' : 'text-[#94a3b8]'
                      }`}
                      style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                    >
                      {title}
                    </div>
                    <div
                      className={`mt-1 text-[13px] font-medium leading-snug ${
                        isActive ? 'text-[#cbd5e1]' : isPast ? 'text-[#b8c9dc]' : 'text-[#8b9cb3]'
                      }`}
                      style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                    >
                      {tagline}
                    </div>
                  </div>

                  <div className="flex w-8 flex-shrink-0 items-center justify-center pt-1">
                    {isPast ? (
                      <Check className="h-[18px] w-[18px] text-[#e8c066]" strokeWidth={2.75} aria-hidden />
                    ) : isActive ? (
                      <span
                        className="h-2.5 w-2.5 rounded-full bg-[#e8c066] shadow-[0_0_10px_rgba(232,192,102,0.85)]"
                        aria-hidden
                      />
                    ) : null}
                  </div>

                  <div
                    className={`pointer-events-none absolute bottom-full left-1/2 z-[200] mb-2 w-[min(240px,calc(100vw-2rem))] max-w-[calc(100%+1rem)] -translate-x-1/2 rounded border border-white/[0.12] p-3.5 text-[13px] font-medium opacity-0 shadow-xl transition-opacity duration-200 group-hover:opacity-100 ${
                      isRTL ? 'text-right' : 'text-left'
                    }`}
                    style={{
                      fontFamily: WORKSPACE_CHAT_FONT,
                      lineHeight: 1.55,
                      background: 'rgba(2,6,23,0.98)',
                      color: 'rgba(245,245,240,0.95)',
                    }}
                  >
                    {tooltip}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
