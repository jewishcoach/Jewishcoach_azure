import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Heart, Brain, Target, Zap } from 'lucide-react';
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
}

export const HudPanel = ({ conversationId }: HudPanelProps) => {
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

  if (!conversationId) {
    return (
      <div className="w-64 flex flex-col items-center justify-center text-white/30 text-sm p-6">
        <Target size={32} className="mb-2 opacity-50" />
        <p>הנתונים יופיעו כאן</p>
      </div>
    );
  }

  const cards: { icon: React.ReactNode; title: string; items?: string[]; value?: string }[] = [];
  if (data?.topic) cards.push({ icon: <Target size={14} />, title: 'נושא', value: data.topic });
  if (data?.emotions?.length) cards.push({ icon: <Heart size={14} />, title: 'רגשות', items: data.emotions });
  if (data?.thought) cards.push({ icon: <Brain size={14} />, title: 'מחשבה', value: data.thought });
  if (data?.gap_name) cards.push({ icon: <Zap size={14} />, title: 'פער', value: `${data.gap_name}${data.gap_score != null ? ` (${data.gap_score})` : ''}` });
  if (data?.forces?.source?.length) cards.push({ icon: <Zap size={14} />, title: 'ערכים', items: data.forces.source });
  if (data?.forces?.nature?.length) cards.push({ icon: <Zap size={14} />, title: 'יכולות', items: data.forces.nature });

  if (cards.length === 0) {
    return (
      <div className="w-64 flex flex-col items-center justify-center text-white/30 text-sm p-6">
        <Target size={32} className="mb-2 opacity-50" />
        <p>הנתונים יופיעו במהלך השיחה</p>
      </div>
    );
  }

  return (
    <div className="w-64 p-4 space-y-3 overflow-y-auto custom-scrollbar">
      {cards.map((card, i) => (
        <motion.div
          key={card.title + i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          className="rounded-[4px] bg-white/5 border border-white/10 p-3"
        >
          <div className="flex items-center gap-2 text-amber-400/90 mb-1.5">
            {card.icon}
            <span className="text-xs font-medium">{card.title}</span>
          </div>
          {card.value && <p className="text-xs text-white/80 leading-relaxed">{card.value}</p>}
          {card.items && (
            <div className="flex flex-wrap gap-1">
              {card.items.map((item, j) => (
                <span key={j} className="text-xs px-2 py-0.5 rounded bg-white/10 text-white/80">
                  {item}
                </span>
              ))}
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
};
