import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BookText, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../../services/api';

interface PersonalJournalProps {
  conversationId: number;
}

export const PersonalJournal = ({ conversationId }: PersonalJournalProps) => {
  const { t, i18n } = useTranslation();
  const [content, setContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [justSaved, setJustSaved] = useState(false);
  const isRTL = i18n.dir() === 'rtl';

  // Fetch journal on mount or conversation change
  useEffect(() => {
    const fetchJournal = async () => {
      try {
        const data = await apiClient.getJournal(conversationId);
        setContent(data.content || '');
      } catch (error) {
        console.error('Error fetching journal:', error);
      }
    };

    if (conversationId) {
      fetchJournal();
    }
  }, [conversationId]);

  // Auto-save with debounce (2 seconds)
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (conversationId && content !== undefined) {
        try {
          setIsSaving(true);
          await apiClient.saveJournal(conversationId, content);
          setIsSaving(false);
          setJustSaved(true);
          
          // Hide "Saved" indicator after 2 seconds
          setTimeout(() => setJustSaved(false), 2000);
        } catch (error) {
          console.error('Error saving journal:', error);
          setIsSaving(false);
        }
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [content, conversationId]);

  return (
    <div className="border-t border-accent/20 bg-primary-light/20 p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <BookText size={16} className="text-accent" />
          <h4 className="text-sm font-semibold text-primary">
            {isRTL ? 'היומן האישי שלי' : 'My Personal Journal'}
          </h4>
        </div>
        
        {/* Save Indicator */}
        <AnimatePresence>
          {(isSaving || justSaved) && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="flex items-center gap-1 text-xs"
            >
              {isSaving ? (
                <span className="text-gray-500">
                  {isRTL ? 'שומר...' : 'Saving...'}
                </span>
              ) : (
                <span className="text-green-600 flex items-center gap-1">
                  <Check size={12} />
                  {isRTL ? 'נשמר' : 'Saved'}
                </span>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className={`
          w-full h-32 p-3 rounded-lg border border-gray-300
          focus:outline-none focus:ring-2 focus:ring-accent/30
          bg-white/90 backdrop-blur-sm
          text-sm text-primary resize-none
          ${isRTL ? 'text-right' : 'text-left'}
        `}
        placeholder={
          isRTL
            ? 'רשום כאן מחשבות, תובנות והרהורים...'
            : 'Write your thoughts, insights, and reflections...'
        }
        dir={isRTL ? 'rtl' : 'ltr'}
      />
    </div>
  );
};




