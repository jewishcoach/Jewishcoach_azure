import { motion } from 'framer-motion';
import { BookOpen } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { ToolCall } from '../../types';
import { ActiveToolRenderer } from './ActiveToolRenderer';
import { SmartInsightsPanel } from './SmartInsightsPanel';
import { PersonalJournal } from './PersonalJournal';
import { ResourceLibrary } from './ResourceLibrary';

interface InsightHubProps {
  conversationId: number | null;
  currentPhase: string;
  activeTool: ToolCall | null;
  onToolSubmit: (submission: { tool_type: string; data: any }) => Promise<void>;
}

export const InsightHub = ({
  conversationId,
  currentPhase,
  activeTool,
  onToolSubmit
}: InsightHubProps) => {
  const { t, i18n } = useTranslation();
  const isRTL = i18n.dir() === 'rtl';

  return (
    <motion.div
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="w-[25%] h-full bg-gradient-to-b from-primary-light/30 to-primary-light/10 border-r border-accent/20 flex flex-col overflow-hidden flex-shrink-0"
    >
      {/* Header */}
      <div className="p-4 border-b border-accent/20 bg-primary-light/50">
        <div className="flex items-center gap-2">
          <BookOpen size={20} className="text-accent" />
          <h2 className="text-lg font-semibold text-primary">
            {isRTL ? 'מרכז התובנות' : 'Insight Hub'}
          </h2>
        </div>
      </div>

      {/* Smart Insights Panel - Always visible with draft/final modes */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {conversationId ? (
          <SmartInsightsPanel
            conversationId={conversationId}
            currentPhase={currentPhase}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center py-12 opacity-50">
            <BookOpen size={48} className="text-accent mb-4" />
            <p className="text-sm text-primary-dark">
              {isRTL
                ? 'התובנות שלך יופיעו כאן במהלך השיחה'
                : 'Your insights will appear here during the conversation'}
            </p>
          </div>
        )}
      </div>

      {/* Active Tool Area (if needed) */}
      {activeTool && (
        <div className="border-t border-accent/20 p-4 bg-white/50">
          <ActiveToolRenderer
            tool={activeTool}
            onSubmit={onToolSubmit}
            language={i18n.language as 'he' | 'en'}
          />
        </div>
      )}

      {/* Personal Journal */}
      {conversationId && (
        <PersonalJournal conversationId={conversationId} />
      )}

      {/* Resource Library */}
      <ResourceLibrary currentPhase={currentPhase} />
    </motion.div>
  );
};

