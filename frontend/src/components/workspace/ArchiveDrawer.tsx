import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { X, MessageSquare, Search, Loader2 } from 'lucide-react';
import type { Conversation } from '../../types';

function phaseLabel(t: (k: string) => string, step: string | undefined): string {
  const s = step || 'S0';
  const key = `phase.${s}`;
  const label = t(key);
  return label === key ? s : label;
}

interface ArchiveDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  conversations: Conversation[];
  /** True while GET /conversations is in flight (first load). */
  listLoading?: boolean;
  activeId: number | null;
  onSelect: (id: number) => void;
  onNewChat: () => void;
  onDelete: (id: number) => void;
  onShare: (id: number) => void;
  isRTL: boolean;
}

export const ArchiveDrawer = ({
  isOpen,
  onClose,
  conversations,
  listLoading = false,
  activeId,
  onSelect,
  onNewChat,
  onDelete,
  onShare,
  isRTL,
}: ArchiveDrawerProps) => {
  const { t, i18n } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const dateLocale = i18n.language?.startsWith('he') ? 'he-IL' : 'en-US';
  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    const q = searchQuery.trim().toLowerCase();
    return conversations.filter((c) => (c.title || '').toLowerCase().includes(q));
  }, [conversations, searchQuery]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/30 z-40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ x: -320 }}
            animate={{ x: 0 }}
            exit={{ x: -320 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 bottom-0 left-0 w-[min(85vw,320px)] max-w-[320px] bg-[#0F172A]/95 backdrop-blur-md border-r border-white/10 z-50 shadow-2xl flex flex-col min-h-0"
          >
            <div className="p-4 border-b border-white/10 flex justify-between items-center shrink-0">
              <h3 className="text-sm font-medium text-white/90">{t('chat.archiveTitle')}</h3>
              <button
                type="button"
                onClick={onClose}
                className="p-2 rounded-xl text-white/60 hover:text-white hover:bg-white/5"
              >
                <X size={18} />
              </button>
            </div>
            <div className="px-4 pt-4 shrink-0">
              <button
                type="button"
                onClick={() => {
                  onNewChat();
                  onClose();
                }}
                className="w-full py-2.5 rounded-xl text-sm font-semibold transition-all border border-[#FCF6BA]/45 bg-gradient-to-br from-[#BF953F] via-[#FCF6BA] to-[#B38728] text-[#0f172a] shadow-sm hover:brightness-105"
              >
                {t('chat.newConversation')}
              </button>
            </div>
            <div className="px-4 py-2 shrink-0">
              <div className="relative">
                <Search size={16} className={`absolute top-1/2 -translate-y-1/2 text-white/40 ${isRTL ? 'right-3' : 'left-3'}`} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t('chat.archiveSearchPlaceholder')}
                  className={`w-full py-2 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/40 text-sm focus:outline-none focus:border-[#FCF6BA]/40 ${isRTL ? 'pr-9 pl-3' : 'pl-9 pr-3'}`}
                  dir={isRTL ? 'rtl' : 'ltr'}
                />
              </div>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar px-2 pb-4">
              {listLoading ? (
                <div className="flex flex-col items-center justify-center gap-3 py-16 text-white/70">
                  <Loader2 className="h-8 w-8 animate-spin text-[#FCF6BA]/90" strokeWidth={2} />
                  <p className="text-xs text-center px-4">{t('chat.loadingConversations')}</p>
                </div>
              ) : conversations.length === 0 ? (
                <div className="text-center py-12 text-white/40">
                  <MessageSquare size={32} className="mx-auto mb-2" />
                  <p className="text-xs">{t('chat.archiveEmpty')}</p>
                </div>
              ) : filtered.length === 0 ? (
                <div className="text-center py-8 text-white/40">
                  <Search size={24} className="mx-auto mb-2" />
                  <p className="text-xs">{t('chat.archiveNoResults')}</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {filtered.map((conv) => (
                    <div
                      key={conv.id}
                      onClick={() => {
                        onSelect(conv.id);
                        onClose();
                      }}
                      className={`
                        px-3 py-2.5 rounded-xl cursor-pointer transition-colors
                        ${activeId === conv.id ? 'bg-[#FCF6BA]/15 text-[#FCF6BA]' : 'text-white/80 hover:bg-white/5'}
                      `}
                    >
                      <div className="flex justify-between items-start gap-2">
                        <span className="text-sm truncate flex-1 min-w-0">{conv.title}</span>
                        <span className="text-xs text-white/40 shrink-0">
                          {new Date(conv.created_at).toLocaleDateString(dateLocale)}
                        </span>
                      </div>
                      <p className="text-[11px] text-white/45 mt-1 leading-snug truncate">
                        {t('chat.archiveMeta', {
                          phase: phaseLabel(t, conv.current_phase),
                          count: conv.message_count ?? conv.messages?.length ?? 0,
                        })}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
