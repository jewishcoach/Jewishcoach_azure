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
      className="rounded-[4px] p-4"
      style={{
        background: 'rgba(255,255,255,0.03)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '0.5px solid rgba(212, 175, 55, 0.2)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.35), 0 0 0 1px rgba(212,175,55,0.05)',
      }}
    >
      <div className="flex items-center gap-2.5 mb-2">
        <span
          className="shrink-0"
          style={{
            color: empty ? 'rgba(212,175,55,0.4)' : 'rgba(212,175,55,0.95)',
            filter: empty ? undefined : 'drop-shadow(0 0 4px rgba(212,175,55,0.3))',
          }}
        >
          {icon}
        </span>
        <span className="text-[13px] font-medium text-white/90 tracking-wide" style={{ fontFamily: 'Cormorant Garamond, Playfair Display, serif', letterSpacing: '0.04em' }}>{title}</span>
      </div>
      {empty ? (
        <p className="text-[13px] text-white/30 italic" style={{ fontFamily: 'Cormorant Garamond, serif', fontStyle: 'italic' }}>
          {placeholder || '—'}
        </p>
      ) : value ? (
        <p className="text-[13px] text-white/85 leading-relaxed" style={{ lineHeight: 1.6, fontFamily: 'Inter, sans-serif', fontWeight: 300 }}>{value}</p>
      ) : items && items.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {items.map((item, j) => (
            <span key={j} className="text-[12px] px-2.5 py-1 rounded-[4px] bg-[#D4AF37]/10 text-white/85 border border-[#D4AF37]/25" style={{ fontFamily: 'Inter, sans-serif' }}>
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
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-5">
        {/* כוחות מקור - luxury card */}
        <section>
          <h4 className="text-[11px] uppercase tracking-[0.2em] text-[#D4AF37]/70 mb-3" style={{ fontFamily: 'Cormorant Garamond, Playfair Display, serif' }}>כוחות מקור</h4>
          <Card
            icon={<Gem size={16} strokeWidth={1.5} />}
            title="ערכים"
            items={data?.forces?.source}
            empty={!hasMekor}
            placeholder="הערכים שעולים בשיחה יופיעו כאן"
          />
        </section>
        {/* כוחות טבע - luxury card */}
        <section>
          <h4 className="text-[11px] uppercase tracking-[0.2em] text-[#D4AF37]/70 mb-3" style={{ fontFamily: 'Cormorant Garamond, Playfair Display, serif' }}>כוחות טבע</h4>
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
