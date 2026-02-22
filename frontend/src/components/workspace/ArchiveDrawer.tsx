import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, MessageSquare, Search } from 'lucide-react';
import type { Conversation } from '../../types';

interface ArchiveDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  conversations: Conversation[];
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
  activeId,
  onSelect,
  onNewChat,
  onDelete,
  onShare,
  isRTL,
}: ArchiveDrawerProps) => {
  const [searchQuery, setSearchQuery] = useState('');
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
            className="fixed inset-0 bg-black/40 z-40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ x: isRTL ? 320 : -320 }}
            animate={{ x: 0 }}
            exit={{ x: isRTL ? 320 : -320 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 bottom-0 w-80 bg-[#0F172A] border-r border-white/10 z-50 shadow-2xl"
            style={{ [isRTL ? 'right' : 'left']: 0 }}
          >
            <div className="p-4 border-b border-white/10 flex justify-between items-center">
              <h3 className="text-sm font-medium text-white/90">ארכיון שיחות</h3>
              <button
                onClick={onClose}
                className="p-2 rounded-[4px] text-white/60 hover:text-white hover:bg-white/5"
              >
                <X size={18} />
              </button>
            </div>
            <button
              onClick={() => {
                onNewChat();
                onClose();
              }}
              className="w-full mx-4 mt-4 py-2.5 rounded-[4px] bg-white/10 hover:bg-white/15 text-white text-sm font-medium transition-colors"
            >
              שיחה חדשה
            </button>
            <div className="px-4 py-2">
              <div className="relative">
                <Search size={16} className={`absolute top-1/2 -translate-y-1/2 text-white/40 ${isRTL ? 'right-3' : 'left-3'}`} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="חיפוש שיחות..."
                  className={`w-full py-2 rounded-[4px] bg-white/5 border border-white/10 text-white placeholder-white/40 text-sm focus:outline-none focus:border-amber-500/50 ${isRTL ? 'pr-9 pl-3' : 'pl-9 pr-3'}`}
                  dir="rtl"
                />
              </div>
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar px-2 pb-4">
              {conversations.length === 0 ? (
                <div className="text-center py-12 text-white/40">
                  <MessageSquare size={32} className="mx-auto mb-2" />
                  <p className="text-xs">אין שיחות</p>
                </div>
              ) : filtered.length === 0 ? (
                <div className="text-center py-8 text-white/40">
                  <Search size={24} className="mx-auto mb-2" />
                  <p className="text-xs">לא נמצאו שיחות</p>
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
                        px-3 py-2.5 rounded-[4px] cursor-pointer transition-colors
                        ${activeId === conv.id ? 'bg-amber-500/20 text-amber-400' : 'text-white/80 hover:bg-white/5'}
                      `}
                    >
                      <div className="flex justify-between items-start gap-2">
                        <span className="text-sm truncate flex-1">{conv.title}</span>
                        <span className="text-xs text-white/40 shrink-0">
                          {new Date(conv.created_at).toLocaleDateString('he-IL')}
                        </span>
                      </div>
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
