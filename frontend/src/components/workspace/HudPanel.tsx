import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Heart, Brain, Target, Zap, Archive, Gem, Layers } from 'lucide-react';
import { apiClient } from '../../services/api';

interface CognitiveData {
  topic?: string;
  emotions?: string[];
  thought?: string;
  action_actual?: string;
  action_desired?: string;
  gap_name?: string;
  gap_score?: number;
  pattern?: string;
  stance?: { gains?: string[]; losses?: string[] };
  forces?: { source?: string[]; nature?: string[] };
}

interface HudPanelProps {
  conversationId: number | null;
  onArchiveClick?: () => void;
}

export const HudPanel = ({ conversationId, onArchiveClick }: HudPanelProps) => {
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
        if (res.exists !== false) setData(res.cognitive_data || {});
      } catch {
        setData(null);
      }
    };
    fetchData();
    interval = setInterval(fetchData, 3000);
    return () => { if (interval) clearInterval(interval); };
  }, [conversationId]);

  const hasMekor = (data?.forces?.source?.length ?? 0) > 0;
  const hasTeva = !!data?.pattern;
  const hasOther = !!(data?.topic || data?.emotions?.length || data?.thought || data?.gap_name);

  const Card = ({ icon, title, items, value, empty }: { icon: React.ReactNode; title: string; items?: string[]; value?: string; empty?: boolean }) => (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="rounded-[4px] bg-white/[0.04] border border-white/[0.08] p-3"
      style={{ borderColor: empty ? 'rgba(255,255,255,0.05)' : undefined }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className={empty ? 'text-[#D4AF37]/40' : 'text-[#D4AF37]/90'}>{icon}</span>
        <span className="text-xs font-medium text-white/90" style={{ fontFamily: 'Playfair Display, serif' }}>{title}</span>
      </div>
      {empty ? (
        <p className="text-xs text-white/25 italic">—</p>
      ) : value ? (
        <p className="text-xs text-white/80 leading-relaxed">{value}</p>
      ) : items && items.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {items.map((item, j) => (
            <span key={j} className="text-xs px-2 py-0.5 rounded-[4px] bg-[#D4AF37]/10 text-white/80 border border-[#D4AF37]/20">
              {item}
            </span>
          ))}
        </div>
      ) : null}
    </motion.div>
  );

  return (
    <div className="w-64 flex flex-col h-full bg-[#020617]/50">
      {/* Archive button - top corner */}
      {onArchiveClick && (
        <div className="p-3 border-b border-white/[0.06] flex justify-end">
          <button
            onClick={onArchiveClick}
            className="p-2 rounded-[4px] text-white/40 hover:text-[#D4AF37]/80 hover:bg-white/5 transition-colors"
            aria-label="ארכיון"
          >
            <Archive size={18} />
          </button>
        </div>
      )}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        {/* כוחות מקור - always visible */}
        <section>
          <h4 className="text-[10px] uppercase tracking-[0.15em] text-[#D4AF37]/60 mb-2" style={{ fontFamily: 'Playfair Display, serif' }}>כוחות מקור</h4>
          <Card
            icon={<Gem size={14} />}
            title="ערכים"
            items={data?.forces?.source}
            empty={!hasMekor}
          />
        </section>
        {/* כוחות טבע - always visible */}
        <section>
          <h4 className="text-[10px] uppercase tracking-[0.15em] text-[#D4AF37]/60 mb-2" style={{ fontFamily: 'Playfair Display, serif' }}>כוחות טבע</h4>
          <Card
            icon={<Layers size={14} />}
            title="דפוס"
            value={data?.pattern}
            empty={!hasTeva}
          />
        </section>
        {/* Other data - when available */}
        {data?.topic && <Card icon={<Target size={14} />} title="נושא" value={data.topic} />}
        {data?.emotions?.length ? <Card icon={<Heart size={14} />} title="רגשות" items={data.emotions} /> : null}
        {data?.thought && <Card icon={<Brain size={14} />} title="מחשבה" value={data.thought} />}
        {data?.gap_name && <Card icon={<Zap size={14} />} title="פער" value={`${data.gap_name}${data.gap_score != null ? ` (${data.gap_score})` : ''}`} />}
        {data?.forces?.nature?.length ? <Card icon={<Zap size={14} />} title="יכולות" items={data.forces!.nature} /> : null}
      </div>
    </div>
  );
};
