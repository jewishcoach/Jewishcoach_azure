import { motion } from 'framer-motion';
import { Plus, MessageSquare, MoreVertical, Share2, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useEffect, useRef, useState } from 'react';
import type { Conversation } from '../types';

interface SidebarProps {
  conversations: Conversation[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onNewChat: () => void;
  onDelete: (id: number) => void;
  onShare: (id: number) => void;
  isRTL: boolean;
}

export const Sidebar = ({ conversations, activeId, onSelect, onNewChat, onDelete, onShare, isRTL }: SidebarProps) => {
  const { t } = useTranslation();
  const [openMenuId, setOpenMenuId] = useState<number | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpenMenuId(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <motion.div
      initial={false} // Disable initial animation to prevent "jumping" on re-render
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 100, opacity: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="w-80 h-full bg-primary border-l border-accent-light/20 flex flex-col flex-shrink-0"
    >
      {/* New Chat Button */}
      <div className="p-4">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-accent to-accent-dark text-white rounded-xl shadow-glow hover:shadow-xl transition-all"
        >
          <Plus size={20} />
          <span className="font-semibold">{t('sidebar.newChat')}</span>
        </motion.button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-2 custom-scrollbar">
        {conversations.length === 0 ? (
          <div className="text-center py-8 text-cream/50">
            <MessageSquare size={40} className="mx-auto mb-2 opacity-30" />
            <p className="text-sm">{t('sidebar.noConversations')}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map((conv) => (
              <div key={conv.id} className="relative" data-conv-id={conv.id}>
                <motion.div
                  whileHover={{ scale: 1.02 }}
                  onClick={() => onSelect(conv.id)}
                  className={`w-full ${isRTL ? 'text-right' : 'text-left'} px-4 py-3 rounded-lg transition-all cursor-pointer ${
                    activeId === conv.id
                      ? 'bg-accent/20 border-2 border-accent text-cream'
                      : 'bg-primary-light/50 text-cream/70 hover:bg-primary-light hover:text-cream'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="font-medium truncate">{conv.title}</div>
                      <div className="text-xs opacity-60 mt-1">
                        {new Date(conv.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuId(openMenuId === conv.id ? null : conv.id);
                      }}
                      className="p-1 rounded-md text-cream/60 hover:text-cream hover:bg-primary-light/60"
                      aria-label={t('sidebar.moreOptions', 'More options')}
                    >
                      <MoreVertical size={16} />
                    </button>
                  </div>
                </motion.div>

                {openMenuId === conv.id && (
                  <div
                    ref={menuRef}
                    className={`absolute ${isRTL ? 'left-4' : 'right-4'} top-12 z-[9999] w-40 rounded-lg bg-white shadow-2xl border border-gray-300`}
                  >
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuId(null);
                        onShare(conv.id);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <Share2 size={14} />
                      {t('sidebar.share', 'Share')}
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuId(null);
                        onDelete(conv.id);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                    >
                      <Trash2 size={14} />
                      {t('sidebar.delete', 'Delete')}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
};

