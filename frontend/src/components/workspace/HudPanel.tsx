import { useEffect, useState, memo } from 'react';
import { Sparkles, Archive, MessageSquarePlus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@clerk/clerk-react';
import { apiClient } from '../../services/api';
import { EnrichmentVideos } from './EnrichmentVideos';
import { WORKSPACE_CHAT_FONT } from '../../constants/workspaceFonts';

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
  stance?: { gains?: string[]; losses?: string[] };
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

/** Compact tag for insight - appears at top of right panel. Long text uses parent panel scroll only. */
const InsightTag = ({ label, value }: { label: string; value: string }) => (
  <div
    className="px-3 py-2 rounded-xl border min-h-[2.5rem]"
    style={{
      background: 'rgba(255, 255, 255, 0.04)',
      borderColor: 'rgba(252, 246, 186, 0.2)',
      fontFamily: WORKSPACE_CHAT_FONT,
    }}
  >
    <span className="text-[11px] uppercase tracking-wider text-[#FCF6BA]/70">{label}</span>
    <p
      className="text-[13px] font-light text-[#F5F5F0]/95 mt-0.5 break-words whitespace-pre-wrap"
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
        const token = await getToken();
        if (token) apiClient.setToken(token);
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
        const token = await getToken();
        if (token) apiClient.setToken(token);
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
    interval = setInterval(fetchData, 3000);
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

  const actionLbl = t('insights.label.action');
  const emotionLbl = t('insights.label.emotion');
  const thoughtLbl = t('insights.label.thought');

  const insightTags: { label: string; value: string }[] = [];

  if (data?.topic && currentIdx >= 1) {
    insightTags.push({ label: t('insights.label.topic'), value: data.topic });
  }
  if (currentIdx >= 2 && emotions.length > 0) {
    insightTags.push({ label: emotionLbl, value: emotions.join(', ') });
  }
  if (currentIdx >= 3 && thought) {
    insightTags.push({ label: thoughtLbl, value: thought });
  }
  if (currentIdx >= 4 && actionActual) {
    insightTags.push({ label: t('insights.label.actionActual'), value: actionActual });
  }
  if (currentIdx >= 5) {
    const ad = data?.action_desired ?? data?.event_actual?.action_desired;
    const ed = data?.emotion_desired ?? data?.event_actual?.emotion_desired;
    const td = data?.thought_desired ?? data?.event_actual?.thought_desired;
    const parts: string[] = [];
    if (ad) parts.push(`${actionLbl}: ${ad}`);
    if (ed) parts.push(`${emotionLbl}: ${ed}`);
    if (td) parts.push(`${thoughtLbl}: ${td}`);
    if (parts.length) insightTags.push({ label: t('insights.label.desired'), value: parts.join('\n') });
  }
  if (gapName && currentIdx >= 6) {
    insightTags.push({ label: t('insights.label.gap'), value: `${gapName}${gapScore != null ? ` (${gapScore}/10)` : ''}` });
  }
  if (pattern && currentIdx >= 7) {
    insightTags.push({ label: t('insights.label.pattern'), value: pattern });
  }
  if (paradigm && currentIdx >= 9) {
    insightTags.push({ label: t('insights.label.paradigm'), value: paradigm });
  }
  if (stanceData && currentIdx >= 11) {
    const gains = stanceData.gains ?? [];
    const losses = stanceData.losses ?? [];
    const parts: string[] = [];
    if (gains.length) parts.push(`${t('insights.label.gains')}: ${gains.join(', ')}`);
    if (losses.length) parts.push(`${t('insights.label.losses')}: ${losses.join(', ')}`);
    if (parts.length) insightTags.push({ label: t('insights.label.oldStance'), value: parts.join('\n') });
  }
  const kmz = data?.kmz_forces ?? data?.forces;
  if (currentIdx >= 12 && kmz) {
    const k = kmz as Record<string, string[] | undefined>;
    const source = k.source_forces ?? k.source ?? [];
    const nature = k.nature_forces ?? k.nature ?? [];
    const parts: string[] = [];
    if (source.length) parts.push(`${t('insights.label.source')}: ${source.join(', ')}`);
    if (nature.length) parts.push(`${t('insights.label.nature')}: ${nature.join(', ')}`);
    if (parts.length) insightTags.push({ label: t('insights.label.kmzForces'), value: parts.join('\n') });
  }

  return (
    <div className="w-full md:w-72 flex flex-col h-full bg-[#1e293b] min-h-0">
      {/* שיחות קודמות + שיחה חדשה — דסקטופ בלבד; במובייל הארכיון בהדר */}
      {(onArchiveClick || onNewChat) && (
        <div className="hidden md:flex md:flex-col p-4 border-b border-white/[0.06] gap-2">
          {onArchiveClick && (
            <button
              type="button"
              onClick={onArchiveClick}
              title={t('chat.previousConversationsHint')}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-white border border-[#E2E4E8] text-[#2E3A56] text-sm font-medium shadow-sm transition-all duration-150 ease-out hover:-translate-y-0.5 hover:bg-slate-300 hover:border-slate-500 hover:shadow-[0_6px_20px_-4px_rgba(51,65,85,0.45)] hover:ring-2 hover:ring-slate-400/55 active:translate-y-0 active:bg-slate-400/90"
              style={{ fontFamily: WORKSPACE_CHAT_FONT }}
            >
              <Archive size={18} strokeWidth={2} className="flex-shrink-0 text-[#2E3A56]" />
              <span>{t('chat.previousConversations')}</span>
            </button>
          )}
          {onNewChat && (
            <button
              type="button"
              onClick={onNewChat}
              disabled={loading}
              title={t('chat.newConversation')}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-sm font-semibold shadow-sm transition-all duration-150 ease-out border border-[#FCF6BA]/45 bg-gradient-to-br from-[#BF953F] via-[#FCF6BA] to-[#B38728] text-[#0f172a] hover:brightness-105 hover:-translate-y-0.5 hover:shadow-[0_6px_20px_-4px_rgba(179,135,40,0.35)] active:translate-y-0 disabled:opacity-45 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:brightness-100"
              style={{ fontFamily: WORKSPACE_CHAT_FONT }}
            >
              <MessageSquarePlus size={18} strokeWidth={2} className="flex-shrink-0 text-[#0f172a]" />
              <span>{t('chat.newConversation')}</span>
            </button>
          )}
        </div>
      )}
      <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col min-h-0">
        {/* תובנות - תגיות למעלה */}
        {insightTags.length > 0 ? (
          <section className="p-5 border-b border-white/[0.06] flex-shrink-0">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={16} className="text-[#FCF6BA]/80" />
              <h4 className="text-[12px] font-light uppercase tracking-[0.15em]" style={{ color: 'rgba(245,245,240,0.8)' }}>{t('chat.insightsTitle')}</h4>
            </div>
            <div className="space-y-2">
              {insightTags.map((tag, i) => (
                <InsightTag key={i} label={tag.label} value={tag.value} />
              ))}
            </div>
          </section>
        ) : conversationId && (
          <section className="p-5 border-b border-white/[0.06] flex-shrink-0">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles size={16} className="text-[#FCF6BA]/50" />
              <h4 className="text-[12px] font-light uppercase tracking-[0.15em]" style={{ color: 'rgba(245,245,240,0.5)' }}>{t('chat.insightsTitle')}</h4>
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
