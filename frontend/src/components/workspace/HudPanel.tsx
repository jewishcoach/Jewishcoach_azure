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

  const Card = ({ icon, title, items, value, empty, placeholder }: { icon: React.ReactNode; title: string; items?: string[]; value?: string; empty?: boolean; placeholder?: string }) => (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="rounded-[4px] p-5"
      style={{
        background: 'rgba(255, 255, 255, 0.03)',
        backdropFilter: 'blur(25px)',
        WebkitBackdropFilter: 'blur(25px)',
        border: '0.5px solid rgba(255, 255, 255, 0.1)',
        boxShadow: '0 12px 40px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.04)',
      }}
    >
      <div className="flex items-center gap-3 mb-3">
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
        <span className="text-[14px] font-light tracking-[0.1em]" style={{ fontFamily: 'Cormorant Garamond, Playfair Display, serif', color: '#F5F5F0' }}>{title}</span>
      </div>
      {empty ? (
        <p className="text-[14px] italic" style={{ fontFamily: 'Cormorant Garamond, serif', fontStyle: 'italic', color: 'rgba(245,245,240,0.4)' }}>
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
    </motion.div>
  );

  return (
    <div className="w-72 flex flex-col h-full bg-[#020617]/50">
      {/* Archive button - top corner */}
      {onArchiveClick && (
        <div className="p-4 border-b border-white/[0.06] flex justify-end">
          <button
            onClick={onArchiveClick}
            className="p-2.5 rounded-[4px] text-white/40 hover:text-[#FCF6BA]/90 hover:bg-white/5 transition-colors"
            aria-label="ארכיון"
          >
            <Archive size={18} strokeWidth={1.5} />
          </button>
        </div>
      )}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-5 space-y-6">
        {/* כוחות מקור - premium ID card */}
        <section>
          <h4 className="text-[12px] font-light uppercase tracking-[0.1em] mb-4" style={{ fontFamily: 'Cormorant Garamond, Playfair Display, serif', color: 'rgba(245,245,240,0.8)' }}>כוחות מקור</h4>
          <Card
            icon={<Gem size={16} strokeWidth={1.5} />}
            title="ערכים"
            items={data?.forces?.source}
            empty={!hasMekor}
            placeholder="הערכים שעולים בשיחה יופיעו כאן"
          />
        </section>
        {/* כוחות טבע - premium ID card */}
        <section>
          <h4 className="text-[12px] font-light uppercase tracking-[0.1em] mb-4" style={{ fontFamily: 'Cormorant Garamond, Playfair Display, serif', color: 'rgba(245,245,240,0.8)' }}>כוחות טבע</h4>
          <Card
            icon={<Layers size={16} strokeWidth={1.5} />}
            title="דפוס"
            value={data?.pattern}
            empty={!hasTeva}
            placeholder="הדפוס שזוהה יופיע כאן"
          />
        </section>
        {/* Other data - when available */}
        {data?.topic && <Card icon={<Target size={16} strokeWidth={1.5} />} title="נושא" value={data.topic} />}
        {data?.emotions?.length ? <Card icon={<Heart size={16} strokeWidth={1.5} />} title="רגשות" items={data.emotions} /> : null}
        {data?.thought && <Card icon={<Brain size={16} strokeWidth={1.5} />} title="מחשבה" value={data.thought} />}
        {data?.gap_name && <Card icon={<Zap size={16} strokeWidth={1.5} />} title="פער" value={`${data.gap_name}${data.gap_score != null ? ` (${data.gap_score})` : ''}`} />}
        {data?.forces?.nature?.length ? <Card icon={<Zap size={16} strokeWidth={1.5} />} title="יכולות" items={data.forces!.nature} /> : null}
      </div>
    </div>
  );
};
