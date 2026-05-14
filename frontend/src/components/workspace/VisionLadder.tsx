/**
 * Vision Ladder - לפי חוברת "תהליך השיבה" מהדורה שלישית
 * שלבים כפי שמופיעים בחוברת
 * לחיצה על שלב – גלילה חכמה להודעה הראשונה באותו שלב
 * במובייל: שלבים עם תובנות מציגים אינדיקציה, לחיצה מציגה popover
 */

import { useState, useEffect, useRef } from 'react';
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
  /** Shown in journey subtitle (desktop). */
  displayName?: string | null;
}

function JourneyProgressRing({ pct, stageFraction, pctCaption }: { pct: number; stageFraction: string; pctCaption: string }) {
  const r = 38;
  const c = 2 * Math.PI * r;
  const clamped = Math.min(100, Math.max(0, pct));
  const offset = c - (clamped / 100) * c;
  return (
    <div className="relative h-[92px] w-[92px] shrink-0" aria-hidden>
      <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.09)" strokeWidth="7" />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke="#c8953a"
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-0.5 px-2 text-center">
        <span className="text-[13px] font-semibold leading-tight text-[#f5f5f0]">{stageFraction}</span>
        <span className="text-[10px] font-normal leading-tight text-[#8b97ae]">{pctCaption}</span>
      </div>
    </div>
  );
}

export const VisionLadder = ({
  currentStep,
  onPhaseClick,
  compact = false,
  conversationId,
  displayName,
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
        className="box-border w-[78px] flex-shrink-0 flex h-full min-h-0 flex-col justify-between py-2 bg-[#1e293b] border-l border-white/[0.07] relative"
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
                  className={`relative w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-medium flex-shrink-0 ${
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
                  className={`text-[9px] leading-tight text-center truncate max-w-full px-0.5 ${
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

  const sessionLabelName = (displayName?.trim() || t('chat.coach')) as string;
  const totalStages = PHASE_IDS.length;
  const stageOrdinal = activePhaseIndex + 1;
  const progressPct = Math.min(
    100,
    Math.round((activePhaseIndex / Math.max(1, totalStages - 1)) * 100),
  );
  const activePhaseKey = PHASE_IDS[activePhaseIndex] ?? 'p0';

  return (
    <div
      className="workspace-ladder flex h-full min-w-[240px] w-full flex-col bg-[#1e293b]"
      dir={isRTL ? 'rtl' : 'ltr'}
    >
      <div className="flex-shrink-0 border-b border-white/[0.07] px-5 pb-5 pt-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#4ecdc4]">{t('ladder.journeyStages')}</p>
        <h2 className="mt-1 text-[18px] font-light tracking-[0.02em] text-[#f5f5f0]" style={{ fontFamily: WORKSPACE_CHAT_FONT }}>
          {t('ladder.journeyTitle')}
        </h2>
        <p className="mt-1 text-[12px] text-[#8b97ae]" style={{ fontFamily: WORKSPACE_CHAT_FONT }}>
          {t('ladder.sessionWith', { name: sessionLabelName })}
        </p>
        <p className="mt-2 text-[11px] text-[#8b97ae]/90">{t('ladder.journeyProgress', { total: totalStages, active: stageOrdinal })}</p>
        <div className="mt-4 flex items-center gap-4">
          <JourneyProgressRing
            pct={progressPct}
            stageFraction={`${stageOrdinal}/${totalStages}`}
            pctCaption={t('ladder.progressPct', { pct: progressPct })}
          />
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-medium text-[#f5f5f0]" style={{ fontFamily: WORKSPACE_CHAT_FONT }}>
              {t(`ladder.${activePhaseKey}`)}
            </p>
            <p className="mt-1 border-s-2 border-[#d4a017] ps-2 text-[11px] leading-snug text-[#c9d4e8]/90" style={{ fontFamily: WORKSPACE_CHAT_FONT }}>
              {t(`ladder.${activePhaseKey}.tagline`)}
            </p>
          </div>
        </div>
      </div>

      <div className="custom-scrollbar flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto overflow-x-visible px-4 py-4">
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
            <div key={phaseId} className="group relative">
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
                className={`flex w-full items-start gap-3 rounded-xl border px-3 py-2.5 text-start transition-colors ${
                  isStepPulsing ? 'vision-ladder-desktop--step-pulse transition-none' : 'transition-all duration-200'
                } ${
                  isClickable ? 'cursor-pointer hover:bg-white/[0.04]' : 'cursor-default'
                } ${
                  isActive
                    ? 'border-[#c8953a]/55 bg-[rgba(200,149,58,0.12)] shadow-[0_0_14px_rgba(200,149,58,0.12)]'
                    : 'border-white/[0.06] bg-transparent'
                }`}
              >
                <div className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center">
                  {isPast ? (
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#2e646a] text-white shadow-sm">
                      <Check className="h-3.5 w-3.5" strokeWidth={2.5} aria-hidden />
                    </span>
                  ) : (
                    <span
                      className={`flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-semibold ${
                        isActive
                          ? 'border-2 border-[#c8953a] bg-[rgba(200,149,58,0.18)] text-[#f5f5f0]'
                          : 'border border-white/[0.08] bg-[#213744] text-[#8b97ae]'
                      }`}
                    >
                      {i + 1}
                    </span>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div
                    className={`text-[13px] font-medium leading-snug ${
                      isActive ? 'text-[#f5f5f0]' : isPast ? 'text-[#f5f5f0]/88' : 'text-[#f5f5f0]/45'
                    }`}
                    style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                  >
                    {title}
                  </div>
                  <div
                    className={`mt-0.5 text-[11px] leading-snug ${isActive ? 'text-[#c9d4e8]/90' : 'text-[#8b97ae]/80'}`}
                    style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                  >
                    {tagline}
                  </div>
                </div>
                <div
                  className={`pointer-events-none absolute left-1/2 top-full z-[100] mt-2 w-[220px] -translate-x-1/2 rounded border border-white/[0.12] p-3 text-[12px] opacity-0 shadow-xl transition-opacity duration-200 group-hover:opacity-100 ${
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
  );
};
