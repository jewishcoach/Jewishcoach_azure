/**
 * Vision Ladder - לפי חוברת "תהליך השיבה" מהדורה שלישית
 * שלבים כפי שמופיעים בחוברת
 * לחיצה על שלב – גלילה חכמה להודעה הראשונה באותו שלב
 * במובייל: שלבים עם תובנות מציגים אינדיקציה, לחיצה מציגה popover
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../../services/api';
import { buildInsightsByPhase, type InsightItem } from '../../utils/insightsByPhase';

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

const CREAM_WHITE = '#F5F5F0';

interface VisionLadderProps {
  currentStep: string;
  onPhaseClick?: (phaseIndex: number) => void;
  /** Compact strip for mobile - narrow vertical dots */
  compact?: boolean;
  /** For compact: fetch insights and show popover on tap */
  conversationId?: number | null;
}

export const VisionLadder = ({ currentStep, onPhaseClick, compact = false, conversationId }: VisionLadderProps) => {
  const { t, i18n } = useTranslation();
  const activePhaseIndex = STEP_TO_PHASE[currentStep] ?? 0;
  const isRTL = i18n.language === 'he' || i18n.language?.startsWith('he');
  const [insightsByPhase, setInsightsByPhase] = useState<Record<number, InsightItem[]>>({});
  const [popoverPhase, setPopoverPhase] = useState<number | null>(null);

  // Fetch insights when compact and conversationId available
  useEffect(() => {
    if (!compact || !conversationId) {
      setInsightsByPhase({});
      return;
    }
    let interval: NodeJS.Timeout | null = null;
    const fetchData = async () => {
      try {
        const res = await apiClient.getConversationInsights(conversationId);
        if (res.exists === false || !res.cognitive_data) return;
        const phase = res.current_stage ?? currentStep;
        const map = buildInsightsByPhase(res.cognitive_data, phase);
        setInsightsByPhase(map);
      } catch {
        setInsightsByPhase({});
      }
    };
    fetchData();
    interval = setInterval(fetchData, 3000);
    return () => { if (interval) clearInterval(interval); };
  }, [compact, conversationId, currentStep]);

  if (compact) {
    return (
      <div
        className="w-[78px] flex-shrink-0 flex flex-col justify-between py-2 h-full bg-[#1e293b] border-l border-white/[0.08] relative"
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
                className="flex flex-col items-center gap-0.5 py-0.5 min-w-0 transition-all"
                aria-label={`${title} - ${scrollHint}`}
              >
                <span
                  className={`relative w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-medium flex-shrink-0 ${
                    isActive ? 'bg-[#FCF6BA]/90 text-[#020617] ring-2 ring-[#B38728]/60' : isPast ? 'bg-white/30 text-white/80' : 'bg-white/15 text-white/50'
                  }`}
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
                    isActive ? 'text-[#FCF6BA]/95' : isPast ? 'text-white/70' : 'text-white/45'
                  }`}
                >
                  {title}
                </span>
              </button>
              {showPopover && insights.length > 0 && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setPopoverPhase(null)}
                    aria-hidden
                  />
                  <div
                    className={`absolute z-50 min-w-[200px] max-w-[280px] rounded-xl p-3 shadow-xl border ${
                      isRTL ? 'end-full me-2 top-1/2 -translate-y-1/2' : 'start-full ms-2 top-1/2 -translate-y-1/2'
                    }`}
                    style={{
                      background: 'rgba(2,6,23,0.98)',
                      borderColor: 'rgba(252,246,186,0.3)',
                      fontFamily: 'Inter, sans-serif',
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

  return (
    <div className="w-full min-w-[240px] flex flex-col h-full bg-[#1e293b] py-8 px-5 workspace-ladder" dir={isRTL ? 'rtl' : 'ltr'}>
      <div className="flex-1 overflow-y-auto overflow-x-visible custom-scrollbar flex flex-col gap-0">
        {PHASE_IDS.map((phaseId, i) => {
          const title = t(`ladder.${phaseId}`);
          const tooltip = t(`ladder.${phaseId}.tooltip`);
          const isActive = i === activePhaseIndex;
          const isPast = i < activePhaseIndex;
          const isLast = i === PHASE_IDS.length - 1;
          const isClickable = !!onPhaseClick;
          const scrollHint = t('ladder.scrollHint');
          return (
            <div key={phaseId} className="flex flex-col items-stretch">
              <div
                role={isClickable ? 'button' : undefined}
                tabIndex={isClickable ? 0 : undefined}
                aria-label={isClickable ? `${title} - ${scrollHint}` : undefined}
                onClick={isClickable ? () => onPhaseClick(i) : undefined}
                onKeyDown={isClickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPhaseClick(i); } } : undefined}
                className={`group relative rounded-xl px-4 py-3 border transition-all duration-300 ${isClickable ? 'cursor-pointer hover:bg-white/[0.06]' : 'cursor-default'}`}
                style={{
                  background: isActive ? 'rgba(212, 175, 55, 0.12)' : 'rgba(255, 255, 255, 0.03)',
                  borderColor: isActive ? 'rgba(212, 175, 55, 0.4)' : 'rgba(255, 255, 255, 0.08)',
                  boxShadow: isActive ? '0 0 12px rgba(212, 175, 55, 0.15)' : 'none',
                }}
              >
                <div
                  className="text-center font-light text-[15px] tracking-[0.06em] leading-snug w-full"
                  style={{
                    color: isActive ? CREAM_WHITE : isPast ? 'rgba(245,245,240,0.6)' : 'rgba(245,245,240,0.35)',
                  }}
                >
                  {title}
                </div>
                <div
                  className={`absolute top-full left-1/2 -translate-x-1/2 mt-2 z-[100] opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none p-3 rounded text-[12px] shadow-xl w-[220px] ${isRTL ? 'text-right' : 'text-left'}`}
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    lineHeight: 1.6,
                    background: 'rgba(2,6,23,0.98)',
                    border: '0.5px solid rgba(255,255,255,0.12)',
                    color: 'rgba(245,245,240,0.95)',
                  }}
                >
                  {tooltip}
                </div>
              </div>
              {!isLast && (
                <div
                  key={`connector-${phaseId}`}
                  className="w-[1px] flex-shrink-0 mx-auto"
                  style={{
                    height: 6,
                    background: 'linear-gradient(to bottom, rgba(212, 175, 55, 0.5), rgba(212, 175, 55, 0.2))',
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
