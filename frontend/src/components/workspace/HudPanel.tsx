import { useEffect, useState, memo } from 'react';
import { Heart, Brain, Target, Zap, Archive } from 'lucide-react';
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
  stance?: { gains?: string[]; losses?: string[] };
  forces?: { source?: string[]; nature?: string[] };
}

interface HudPanelProps {
  conversationId: number | null;
  currentPhase?: string;
  onArchiveClick?: () => void;
}

export const HudPanel = memo(({ conversationId, currentPhase = 'S0', onArchiveClick }: HudPanelProps) => {
  const [data, setData] = useState<CognitiveData | null>(null);

  useEffect(() => {
    if (!conversationId) {
      setData(null);
      return;
    }
    let interval: NodeJS.Timeout | null = null;
    const fetchData = async () => {
      try {
        const res = await apiClient.getConversationInsights(conversationId);
        if (res.exists === false) return;
        const next = res.cognitive_data || {};
        setData((prev) => {
          if (prev && JSON.stringify(prev) === JSON.stringify(next)) return prev;
          return next;
        });
      } catch {
        setData(null);
      }
    };
    fetchData();
    interval = setInterval(fetchData, 5000);
    return () => { if (interval) clearInterval(interval); };
  }, [conversationId]);

  const emotions = data?.emotions ?? data?.event_actual?.emotions_list ?? [];
  const thought = data?.thought ?? data?.event_actual?.thought_content;
  const gapName = data?.gap_name ?? data?.gap_analysis?.name;
  const gapScore = data?.gap_score ?? data?.gap_analysis?.score;

  const Card = ({ icon, title, items, value, empty, placeholder }: { icon: React.ReactNode; title: string; items?: string[]; value?: string; empty?: boolean; placeholder?: string }) => (
    <div
      className="rounded-[4px] p-6 workspace-hud-card min-h-[100px]"
      style={{
        background: 'rgba(255, 255, 255, 0.03)',
        backdropFilter: 'blur(25px)',
        WebkitBackdropFilter: 'blur(25px)',
        border: '0.5px solid rgba(255, 255, 255, 0.1)',
        boxShadow: '0 12px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04), 0 0 0 1px rgba(212,175,55,0.06)',
      }}
    >
      <div className="flex items-center gap-4 mb-4">
        <span
          className="shrink-0"
          style={{
            color: empty ? 'rgba(252,246,186,0.35)' : 'rgba(252,246,186,0.95)',
            filter: 'drop-shadow(0 0 5px rgba(212, 175, 55, 0.5))',
            strokeWidth: 1,
          }}
        >
          {icon}
        </span>
        <span className="text-[14px] font-light tracking-[0.1em]" style={{ fontFamily: "'Cormorant Garamond', 'Playfair Display', 'Heebo', serif", color: '#F5F5F0' }}>{title}</span>
      </div>
      {empty ? (
        <p className="text-[14px] italic" style={{ fontFamily: "'Cormorant Garamond', 'Heebo', serif", fontStyle: 'italic', color: 'rgba(245,245,240,0.4)' }}>
          {placeholder || '—'}
        </p>
      ) : value ? (
        <p className="text-[14px] leading-relaxed" style={{ lineHeight: 1.7, fontFamily: 'Inter, sans-serif', fontWeight: 300, color: 'rgba(245,245,240,0.9)' }}>{value}</p>
      ) : items && items.length > 0 ? (
        <div className="flex flex-wrap gap-2.5">
          {items.map((item, j) => (
            <span key={j} className="text-[13px] px-3 py-1.5 rounded-[4px] border" style={{ fontFamily: 'Inter, sans-serif', background: 'rgba(255,255,255,0.05)', borderColor: 'rgba(252,246,186,0.25)', color: 'rgba(245,245,240,0.9)' }}>
              {item}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );

  return (
    <div className="w-full md:w-72 flex flex-col h-full bg-[#020617]/50 min-h-0">
      {/* Archive button - top corner */}
      {onArchiveClick && (
        <div className="p-5 border-b border-white/[0.06] flex justify-end">
          <button
            onClick={onArchiveClick}
            className="p-3 rounded-[4px] text-white/40 hover:text-[#FCF6BA]/95 hover:bg-white/5 hover:[filter:drop-shadow(0_0_6px_rgba(212,175,55,0.4))] transition-colors"
            aria-label="ארכיון"
          >
            <Archive size={18} strokeWidth={1.5} />
          </button>
        </div>
      )}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-8">
        {/* נושא האימון - תגית לפי השיחה (כמו במערכת הקודמת) */}
        {data?.topic && <Card icon={<Target size={16} strokeWidth={1.5} />} title="נושא האימון" value={data.topic} />}
        {emotions.length ? <Card icon={<Heart size={16} strokeWidth={1.5} />} title="רגשות" items={emotions} /> : null}
        {thought && <Card icon={<Brain size={16} strokeWidth={1.5} />} title="מחשבה" value={thought} />}
        {gapName && <Card icon={<Zap size={16} strokeWidth={1.5} />} title="פער" value={`${gapName}${gapScore != null ? ` (${gapScore})` : ''}`} />}

        {/* סרטוני העשרה - מתחת לכוחות מקור, מותאם למובייל */}
        <EnrichmentVideos currentPhase={currentPhase} />
      </div>
    </div>
  );
});

HudPanel.displayName = 'HudPanel';
