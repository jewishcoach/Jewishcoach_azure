import { useEffect, useState, memo } from 'react';
import type { ReactNode } from 'react';
import { Sparkles, Archive, MessageSquarePlus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@clerk/clerk-react';
import { apiClient } from '../../services/api';
import { INSIGHTS_POLL_INTERVAL_MS, refreshInsightsAuthToken } from '../../constants/insightsPolling';
import { EnrichmentVideos } from './EnrichmentVideos';
import { WORKSPACE_CHAT_FONT } from '../../constants/workspaceFonts';
import { buildActualInsightSections, buildDesiredInsightSections } from '../../utils/formatMezuyDesiredInsights';

interface CognitiveData {
  topic?: string;
  emotions?: string[];
  event_actual?: {
    emotions_list?: string[];
    thought_content?: string;
    action_content?: string;
    action_desired?: string;
    emotion_desired?: string;
    thought_desired?: string;
  };
  thought?: string;
  action_actual?: string;
  action_desired?: string;
  emotion_desired?: string;
  thought_desired?: string;
  gap_name?: string;
  gap_score?: number;
  gap_analysis?: { name?: string; score?: number };
  pattern?: string;
  pattern_id?: { name?: string; paradigm?: string };
  paradigm?: string;
  stance?: {
    reality_belief?: string;
    activation_trigger?: string;
    gains?: string[];
    losses?: string[];
  };
  forces?: { source?: string[]; nature?: string[] };
  kmz_forces?: { source_forces?: string[]; nature_forces?: string[] };
}

interface HudPanelProps {
  conversationId: number | null;
  currentPhase?: string;
  loading?: boolean;
  onArchiveClick?: () => void;
  /** שיחה חדשה — מתחת לכפתור שיחות קודמות */
  onNewChat?: () => void;
}

/** כרטיס תובנות עם כותרת ראשית ושלושת תתי־הנושאים (מעשה / רגשות / אמירה) */
const InsightSubsectionsCard = ({
  title,
  sections,
}: {
  title: string;
  sections: { heading: string; body: string }[];
}) => (
  <div
    className="min-h-[2.5rem] rounded-xl border border-white/[0.07] bg-[#1c2636] px-3 py-2.5"
    style={{ fontFamily: WORKSPACE_CHAT_FONT }}
  >
    <span className="text-[11px] font-semibold uppercase tracking-wider text-[#4ecdc4]">{title}</span>
    <div className="mt-2 space-y-3">
      {sections.map((s, i) => (
        <div key={i}>
          <div className="text-[11px] font-semibold tracking-wide text-[#d4a017]/95">{s.heading}</div>
          <p
            className="mt-0.5 break-words whitespace-pre-wrap text-[13px] font-light text-[#e8e4dc]/95"
            style={{ lineHeight: 1.45 }}
          >
            {s.body}
          </p>
        </div>
      ))}
    </div>
  </div>
);

const InsightTag = ({ label, value }: { label: string; value: string }) => (
  <div
    className="min-h-[2.5rem] rounded-xl border border-white/[0.07] bg-[#1c2636] px-3 py-2"
    style={{ fontFamily: WORKSPACE_CHAT_FONT }}
  >
    <span className="text-[11px] font-semibold uppercase tracking-wider text-[#4ecdc4]">{label}</span>
    <p
      className="mt-0.5 border-s-2 border-[#d4a017] ps-2 break-words whitespace-pre-wrap text-[13px] font-light text-[#e8e4dc]/95"
      style={{ lineHeight: 1.45 }}
    >
      {value}
    </p>
  </div>
);

export const HudPanel = memo(({ conversationId, currentPhase = 'S0', loading = false, onArchiveClick, onNewChat }: HudPanelProps) => {
  const { t } = useTranslation();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [data, setData] = useState<CognitiveData | null>(null);
  const [insightsPhase, setInsightsPhase] = useState<string>(currentPhase);
  const [wasLoading, setWasLoading] = useState(false);

  // Track loading transition to trigger immediate refetch when message send completes
  useEffect(() => {
    if (wasLoading && !loading && conversationId && isLoaded && isSignedIn) {
      setWasLoading(false);
      (async () => {
        await refreshInsightsAuthToken(getToken, (t) => apiClient.setToken(t));
        try {
          const res = await apiClient.getConversationInsights(conversationId);
          if (res.exists !== false && res.cognitive_data) {
            setData(res.cognitive_data);
            if (res.current_stage) setInsightsPhase(res.current_stage);
          }
        } catch {
          /* ignore */
        }
      })();
    } else if (loading) {
      setWasLoading(true);
    }
  }, [loading, wasLoading, conversationId, isLoaded, isSignedIn, getToken]);

  useEffect(() => {
    if (!conversationId) {
      setData(null);
      setInsightsPhase('S0');
      return;
    }
    if (!isLoaded || !isSignedIn) return;

    let interval: NodeJS.Timeout | null = null;
    const fetchData = async () => {
      try {
        await refreshInsightsAuthToken(getToken, (t) => apiClient.setToken(t));
        const res = await apiClient.getConversationInsights(conversationId);
        if (res.exists === false) return;
        const next = res.cognitive_data || {};
        if (res.current_stage) setInsightsPhase(res.current_stage);
        if (import.meta.env.DEV && Object.keys(next).length > 0) {
          console.log('[HudPanel] Insights:', { currentPhase, insightsPhase: res.current_stage, cognitive_data: next });
        }
        setData((prev) => {
          if (prev && JSON.stringify(prev) === JSON.stringify(next)) return prev;
          return next;
        });
      } catch {
        setData(null);
      }
    };
    fetchData();
    interval = setInterval(fetchData, INSIGHTS_POLL_INTERVAL_MS);
    return () => { if (interval) clearInterval(interval); };
  }, [conversationId, isLoaded, isSignedIn, getToken]);

  const emotions = data?.emotions ?? data?.event_actual?.emotions_list ?? [];
  const thought = data?.thought ?? data?.event_actual?.thought_content;
  const actionActual = data?.action_actual ?? data?.event_actual?.action_content;
  const gapName = data?.gap_name ?? data?.gap_analysis?.name;
  const gapScore = data?.gap_score ?? data?.gap_analysis?.score;
  const pattern = data?.pattern ?? data?.pattern_id?.name;
  const paradigm = data?.paradigm ?? data?.pattern_id?.paradigm;
  const stanceData = data?.stance;

  const stepIndex = (s: string) => parseInt(s.replace('S', ''), 10) || 0;
  // Use the more advanced of currentPhase (from last message) or insightsPhase (from API) for display
  const phaseForDisplay = currentPhase && currentPhase !== 'S0' ? currentPhase : insightsPhase;
  const currentIdx = stepIndex(phaseForDisplay);

  type HudPiece =
    | { kind: 'tag'; label: string; value: string }
    | { kind: 'mezuy'; sections: { heading: string; body: string }[] }
    | { kind: 'desired'; sections: { heading: string; body: string }[] };

  const insightPieces: HudPiece[] = [];

  if (data?.topic && currentIdx >= 1) {
    insightPieces.push({ kind: 'tag', label: t('insights.label.topic'), value: data.topic });
  }

  const mezuySections = buildActualInsightSections(t, currentIdx, emotions, thought, actionActual);
  if (mezuySections.length > 0) {
    insightPieces.push({ kind: 'mezuy', sections: mezuySections });
  }

  if (currentIdx >= 5) {
    const ad = data?.action_desired ?? data?.event_actual?.action_desired;
    const ed = data?.emotion_desired ?? data?.event_actual?.emotion_desired;
    const td = data?.thought_desired ?? data?.event_actual?.thought_desired;
    const desiredSections = buildDesiredInsightSections(t, ad, ed, td);
    if (desiredSections.length > 0) {
      insightPieces.push({ kind: 'desired', sections: desiredSections });
    }
  }
  if (gapName && currentIdx >= 6) {
    insightPieces.push({
      kind: 'tag',
      label: t('insights.label.gap'),
      value: `${gapName}${gapScore != null ? ` (${gapScore}/10)` : ''}`,
    });
  }
  if (pattern && currentIdx >= 7) {
    insightPieces.push({ kind: 'tag', label: t('insights.label.pattern'), value: pattern });
  }
  if (paradigm && currentIdx >= 9) {
    insightPieces.push({ kind: 'tag', label: t('insights.label.paradigm'), value: paradigm });
  }
  if (stanceData && currentIdx >= 10) {
    const rb = stanceData.reality_belief?.trim();
    const trig = stanceData.activation_trigger?.trim();
    const stanceParts: string[] = [];
    if (rb) stanceParts.push(`${t('insights.label.stanceReality')}: ${rb}`);
    if (trig) stanceParts.push(`${t('insights.label.stanceTrigger')}: ${trig}`);
    if (stanceParts.length) {
      insightPieces.push({ kind: 'tag', label: t('insights.label.stance'), value: stanceParts.join('\n') });
    }
  }
  if (stanceData && currentIdx >= 11) {
    const gains = stanceData.gains ?? [];
    const losses = stanceData.losses ?? [];
    const parts: string[] = [];
    if (gains.length) parts.push(`${t('insights.label.gains')}: ${gains.join(', ')}`);
    if (losses.length) parts.push(`${t('insights.label.losses')}: ${losses.join(', ')}`);
    if (parts.length) {
      insightPieces.push({
        kind: 'tag',
        label: t('insights.label.profitLossTable'),
        value: parts.join('\n'),
      });
    }
  }
  const kmz = data?.kmz_forces ?? data?.forces;
  if (currentIdx >= 12 && kmz) {
    const k = kmz as Record<string, string[] | undefined>;
    const source = k.source_forces ?? k.source ?? [];
    const nature = k.nature_forces ?? k.nature ?? [];
    const parts: string[] = [];
    if (source.length) parts.push(`${t('insights.label.source')}: ${source.join(', ')}`);
    if (nature.length) parts.push(`${t('insights.label.nature')}: ${nature.join(', ')}`);
    if (parts.length) {
      insightPieces.push({ kind: 'tag', label: t('insights.label.kmzForces'), value: parts.join('\n') });
    }
  }

  const renderInsightPiece = (piece: HudPiece, i: number): ReactNode => {
    if (piece.kind === 'tag') {
      return <InsightTag key={i} label={piece.label} value={piece.value} />;
    }
    if (piece.kind === 'mezuy') {
      return <InsightSubsectionsCard key={i} title={t('insights.card.actual')} sections={piece.sections} />;
    }
    return <InsightSubsectionsCard key={i} title={t('insights.card.desiredBlock')} sections={piece.sections} />;
  };

  return (
    <div className="w-full md:w-72 flex flex-col h-full bg-[#1e293b] min-h-0 min-w-0 overflow-x-hidden">
      {/* שיחות קודמות + שיחה חדשה — דסקטופ בלבד; במובייל הארכיון בהדר */}
      {(onArchiveClick || onNewChat) && (
        <div className="hidden md:flex md:flex-col gap-2 border-b border-white/[0.07] p-4 overflow-x-hidden">
          {onArchiveClick && (
            <button
              type="button"
              onClick={onArchiveClick}
              title={t('chat.previousConversationsHint')}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/[0.07] bg-[#1c2636] px-3 py-2.5 text-sm font-medium text-[#e8e4dc] transition-colors hover:bg-[#243044]"
              style={{ fontFamily: WORKSPACE_CHAT_FONT }}
            >
              <Archive size={18} strokeWidth={2} className="flex-shrink-0 text-[#e8e4dc]" />
              <span>{t('chat.previousConversations')}</span>
            </button>
          )}
          {onNewChat && (
            <button
              type="button"
              onClick={onNewChat}
              disabled={loading}
              title={t('chat.newConversation')}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-[#c8953a]/40 bg-[rgba(200,149,58,0.1)] px-3 py-2.5 text-sm font-semibold text-[#f0e6d2] transition-colors hover:bg-[rgba(200,149,58,0.16)] disabled:cursor-not-allowed disabled:opacity-45"
              style={{ fontFamily: WORKSPACE_CHAT_FONT }}
            >
              <MessageSquarePlus size={18} strokeWidth={2} className="flex-shrink-0 text-[#e8d4a8]" />
              <span>{t('chat.newConversation')}</span>
            </button>
          )}
        </div>
      )}
      <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar flex flex-col min-h-0 min-w-0">
        {/* תובנות - תגיות למעלה */}
        {insightPieces.length > 0 ? (
          <section className="flex-shrink-0 border-b border-white/[0.07] p-5">
            <div className="mb-3 flex items-center gap-2">
              <Sparkles size={16} className="text-[#4ecdc4]" />
              <h4 className="text-[12px] font-semibold uppercase tracking-[0.12em] text-[#4ecdc4]">{t('chat.insightsTitle')}</h4>
            </div>
            <div className="space-y-2">
              {insightPieces.map((piece, i) => renderInsightPiece(piece, i))}
            </div>
          </section>
        ) : conversationId && (
          <section className="flex-shrink-0 border-b border-white/[0.07] p-5">
            <div className="mb-2 flex items-center gap-2">
              <Sparkles size={16} className="text-[#4ecdc4]/55" />
              <h4 className="text-[12px] font-semibold uppercase tracking-[0.12em] text-[#4ecdc4]/70">{t('chat.insightsTitle')}</h4>
            </div>
            <p className="text-[11px] text-[#F5F5F0]/50" style={{ fontFamily: WORKSPACE_CHAT_FONT }}>
              {t('chat.insightsPlaceholder')}
            </p>
          </section>
        )}
        {/* סרטוני העשרה - צד ימין למטה */}
        <div className="mt-auto flex-shrink-0 p-5">
          <EnrichmentVideos currentPhase={currentPhase} />
        </div>
      </div>
    </div>
  );
});

HudPanel.displayName = 'HudPanel';
