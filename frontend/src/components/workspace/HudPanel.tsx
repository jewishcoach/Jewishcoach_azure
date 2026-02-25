import { useEffect, useState, memo } from 'react';
import { Sparkles, Archive } from 'lucide-react';
import { apiClient } from '../../services/api';
import { EnrichmentVideos } from './EnrichmentVideos';

interface CognitiveData {
  topic?: string;
  emotions?: string[];
  event_actual?: { emotions_list?: string[]; thought_content?: string; action_content?: string };
  thought?: string;
  action_actual?: string;
  action_desired?: string;
  gap_name?: string;
  gap_score?: number;
  gap_analysis?: { name?: string; score?: number };
  pattern?: string;
  pattern_id?: { name?: string };
  stance?: { gains?: string[]; losses?: string[] };
  forces?: { source?: string[]; nature?: string[] };
}

interface HudPanelProps {
  conversationId: number | null;
  currentPhase?: string;
  loading?: boolean;
  onArchiveClick?: () => void;
}

/** Compact tag for insight - appears at top of right panel */
const InsightTag = ({ label, value }: { label: string; value: string }) => (
  <div
    className="px-3 py-2 rounded-xl border"
    style={{
      background: 'rgba(255, 255, 255, 0.04)',
      borderColor: 'rgba(252, 246, 186, 0.2)',
      fontFamily: 'Inter, sans-serif',
    }}
  >
    <span className="text-[11px] uppercase tracking-wider text-[#FCF6BA]/70">{label}</span>
    <p className="text-[13px] font-light text-[#F5F5F0]/95 mt-0.5">{value}</p>
  </div>
);

export const HudPanel = memo(({ conversationId, currentPhase = 'S0', loading = false, onArchiveClick }: HudPanelProps) => {
  const [data, setData] = useState<CognitiveData | null>(null);
  const [insightsPhase, setInsightsPhase] = useState<string>(currentPhase);
  const [wasLoading, setWasLoading] = useState(false);

  // Track loading transition to trigger immediate refetch when message send completes
  useEffect(() => {
    if (wasLoading && !loading && conversationId) {
      setWasLoading(false);
      apiClient.getConversationInsights(conversationId).then((res) => {
        if (res.exists !== false && res.cognitive_data) {
          setData(res.cognitive_data);
          if (res.current_stage) setInsightsPhase(res.current_stage);
        }
      }).catch(() => {});
    } else if (loading) {
      setWasLoading(true);
    }
  }, [loading, wasLoading, conversationId]);

  useEffect(() => {
    if (!conversationId) {
      setData(null);
      setInsightsPhase('S0');
      return;
    }
    let interval: NodeJS.Timeout | null = null;
    const fetchData = async () => {
      try {
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
  }, [conversationId]);

  const emotions = data?.emotions ?? data?.event_actual?.emotions_list ?? [];
  const thought = data?.thought ?? data?.event_actual?.thought_content;
  const actionActual = data?.action_actual ?? data?.event_actual?.action_content;
  const gapName = data?.gap_name ?? data?.gap_analysis?.name;
  const gapScore = data?.gap_score ?? data?.gap_analysis?.score;
  const pattern = data?.pattern ?? data?.pattern_id?.name;

  const stepIndex = (s: string) => parseInt(s.replace('S', ''), 10) || 0;
  // Use the more advanced of currentPhase (from last message) or insightsPhase (from API) for display
  const phaseForDisplay = currentPhase && currentPhase !== 'S0' ? currentPhase : insightsPhase;
  const currentIdx = stepIndex(phaseForDisplay);

  const insightTags: { label: string; value: string }[] = [];

  if (data?.topic && currentIdx >= 1) {
    insightTags.push({ label: 'נושא האימון', value: data.topic });
  }
  if (currentIdx >= 2 && (emotions.length > 0 || thought || actionActual)) {
    const parts: string[] = [];
    if (emotions.length) parts.push(emotions.slice(0, 3).join(', ') + (emotions.length > 3 ? '...' : ''));
    if (thought) parts.push((thought.length > 40 ? thought.slice(0, 40) + '...' : thought));
    if (actionActual) parts.push(actionActual.length > 40 ? actionActual.slice(0, 40) + '...' : actionActual);
    if (parts.length) insightTags.push({ label: 'מצוי (סיכום 3 המסכים)', value: parts.join(' · ') });
  }
  if (gapName && currentIdx >= 6) {
    insightTags.push({ label: 'פער', value: `${gapName}${gapScore != null ? ` (${gapScore}/10)` : ''}` });
  }
  if (pattern && currentIdx >= 7) {
    insightTags.push({ label: 'דפוס', value: pattern });
  }
  if (data?.action_desired && currentIdx >= 5) {
    const v = data.action_desired;
    insightTags.push({ label: 'רצוי', value: v.length > 50 ? v.slice(0, 50) + '...' : v });
  }

  return (
    <div className="w-full md:w-72 flex flex-col h-full bg-[#1e293b] min-h-0">
      {/* Archive button - top corner */}
      {onArchiveClick && (
        <div className="p-5 border-b border-white/[0.06] flex justify-end">
          <button
            onClick={onArchiveClick}
            className="p-3 rounded-xl text-white/40 hover:text-[#FCF6BA]/95 hover:bg-white/5 hover:[filter:drop-shadow(0_0_6px_rgba(212,175,55,0.4))] transition-colors"
            aria-label="ארכיון"
          >
            <Archive size={18} strokeWidth={1.5} />
          </button>
        </div>
      )}
      <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col min-h-0">
        {/* תובנות - תגיות למעלה, מצטברות לפי שלב */}
        {insightTags.length > 0 && (
          <section className="p-5 border-b border-white/[0.06] flex-shrink-0">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={16} className="text-[#FCF6BA]/80" />
              <h4 className="text-[12px] font-light uppercase tracking-[0.15em]" style={{ color: 'rgba(245,245,240,0.8)' }}>תובנות</h4>
            </div>
            <div className="space-y-2">
              {insightTags.map((tag, i) => (
                <InsightTag key={i} label={tag.label} value={tag.value} />
              ))}
            </div>
          </section>
        )}
        <div className="flex-1 overflow-y-auto p-5">
          <EnrichmentVideos currentPhase={currentPhase} />
        </div>
      </div>
    </div>
  );
});

HudPanel.displayName = 'HudPanel';
