import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, ChevronDown, ChevronUp } from 'lucide-react';
import { getVideosForStage } from '../../data/stageVideos';

interface EnrichmentVideosProps {
  currentPhase: string;
}

export const EnrichmentVideos = ({ currentPhase }: EnrichmentVideosProps) => {
  const { i18n } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);
  const isHe = i18n.language === 'he';
  const videos = getVideosForStage(currentPhase);
  const title = isHe ? 'סרטוני העשרה' : 'Enrichment Videos';

  if (videos.length === 0) return null;

  return (
    <section className="mt-4 pt-4 border-t border-white/[0.08]">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between gap-2 py-2 text-right hover:text-[#FCF6BA]/95 transition-colors"
        style={{ fontFamily: "'Cormorant Garamond', 'Heebo', serif", color: 'rgba(245,245,240,0.9)' }}
      >
        <span className="flex items-center gap-2">
          <Play size={14} strokeWidth={1.5} className="text-[#FCF6BA]/80" />
          <span className="text-[13px] font-light tracking-[0.06em]">{title}</span>
        </span>
        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-3 pt-2">
              {videos.map((v, i) => (
                <div
                  key={`${v.videoId}-${i}`}
                  className="rounded-[4px] overflow-hidden"
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '0.5px solid rgba(255,255,255,0.1)',
                  }}
                >
                  <p className="text-[11px] px-2 py-1 text-[#F5F5F0]/70" style={{ fontFamily: 'Inter, sans-serif' }}>
                    {isHe ? v.titleHe : v.titleEn}
                  </p>
                  <div className="relative w-full aspect-video max-h-[140px] sm:max-h-[180px]">
                    <iframe
                      title={isHe ? v.titleHe : v.titleEn}
                      src={`https://www.youtube.com/embed/${v.videoId}?rel=0`}
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                      className="absolute inset-0 w-full h-full"
                    />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
};
