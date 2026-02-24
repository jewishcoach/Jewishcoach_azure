import { useState } from 'react';
import Calendar from 'react-calendar';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Calendar as CalendarIcon, TrendingUp } from 'lucide-react';
import 'react-calendar/dist/Calendar.css';

interface Conversation {
  id: number;
  title: string;
  created_at: string;
  current_phase: string;
  message_count: number;
}

interface CoachingCalendarProps {
  conversations: Conversation[];
  variant?: 'dark' | 'light';
}

const LIGHT = {
  card: 'bg-white rounded-2xl p-6 border border-gray-200 shadow-sm',
  title: 'text-[#2E3A56]',
  muted: 'text-[#5A6B8A]',
  accent: 'text-[#E02C26]',
  accentBg: 'bg-[rgba(224,44,38,0.08)]',
  item: 'bg-gray-50 border border-gray-200',
};
const DARK = {
  card: 'bg-white/[0.04] rounded-2xl p-6 border border-white/[0.08]',
  title: 'text-[#F5F5F0]',
  muted: 'text-[#F5F5F0]/70',
  accent: 'text-[#FCF6BA]',
  accentBg: 'bg-[#FCF6BA]/10',
  item: 'bg-white/[0.06] border border-white/[0.1]',
};

export const CoachingCalendar = ({ conversations, variant = 'dark' }: CoachingCalendarProps) => {
  const theme = variant === 'light' ? LIGHT : DARK;
  const { t, i18n } = useTranslation();
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  // Group conversations by date
  const conversationsByDate: { [key: string]: Conversation[] } = {};
  conversations.forEach((conv) => {
    const date = new Date(conv.created_at).toDateString();
    if (!conversationsByDate[date]) {
      conversationsByDate[date] = [];
    }
    conversationsByDate[date].push(conv);
  });

  // Check if a date has conversations
  const hasConversations = (date: Date) => {
    const dateStr = date.toDateString();
    return conversationsByDate[dateStr] !== undefined;
  };

  // Get conversations for selected date
  const getConversationsForDate = (date: Date) => {
    const dateStr = date.toDateString();
    return conversationsByDate[dateStr] || [];
  };

  // Custom tile content - add dots for dates with conversations
  const tileContent = ({ date, view }: { date: Date; view: string }) => {
    if (view === 'month' && hasConversations(date)) {
      return (
        <div className="flex justify-center mt-1">
          <div className="w-1.5 h-1.5 rounded-full bg-accent"></div>
        </div>
      );
    }
    return null;
  };

  // Custom tile class
  const tileClassName = ({ date, view }: { date: Date; view: string }) => {
    if (view === 'month' && hasConversations(date)) {
      return 'has-coaching';
    }
    return '';
  };

  const selectedConversations = selectedDate ? getConversationsForDate(selectedDate) : [];

  return (
    <div className="space-y-4">
      {/* Calendar */}
      <motion.div
        className={theme.card}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-center gap-2 mb-4">
          <CalendarIcon className={`w-5 h-5 ${theme.accent}`} />
          <h3 className={`text-lg font-bold ${theme.title}`}>{t('calendar.title')}</h3>
        </div>

        <div className={`coaching-calendar ${variant === 'light' ? 'coaching-calendar-light' : 'coaching-calendar-dark'}`} dir="ltr">
          <Calendar
            onChange={(value) => setSelectedDate(value as Date)}
            value={selectedDate}
            tileContent={tileContent}
            tileClassName={tileClassName}
            locale={i18n.language === 'he' ? 'he-IL' : 'en-US'}
            className="w-full border-none"
          />
        </div>

        {/* Legend */}
        <div className={`flex items-center gap-2 mt-4 text-sm ${theme.muted}`}>
          <div className={`w-2 h-2 rounded-full ${variant === 'light' ? 'bg-[#E02C26]' : 'bg-[#FCF6BA]'}`}></div>
          <span>{t('calendar.daysWithCoaching')}</span>
        </div>
      </motion.div>

      {/* Selected Date Details */}
      <AnimatePresence>
        {selectedDate && selectedConversations.length > 0 && (
          <motion.div
            className={theme.card}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <div className="flex items-center gap-2 mb-4">
              <MessageSquare className={`w-5 h-5 ${theme.accent}`} />
              <h3 className={`text-lg font-bold ${theme.title}`}>
                {t('calendar.sessionsOn')}{selectedDate.toLocaleDateString(i18n.language === 'he' ? 'he-IL' : 'en-US')}
              </h3>
            </div>

            <div className="space-y-3">
              {selectedConversations.map((conv) => (
                <motion.div
                  key={conv.id}
                  className={`p-4 rounded-lg ${theme.item}`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  whileHover={{ scale: 1.02 }}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className={`font-medium ${theme.title}`}>{conv.title}</div>
                      <div className={`text-sm mt-1 ${theme.muted}`}>
                        {new Date(conv.created_at).toLocaleTimeString(i18n.language === 'he' ? 'he-IL' : 'en-US', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <div className={`flex items-center gap-1 ${theme.muted}`}>
                        <MessageSquare className={`w-4 h-4 ${theme.accent}`} />
                        <span>{conv.message_count} {t('calendar.messages')}</span>
                      </div>
                      {conv.current_phase && (
                        <div className={`flex items-center gap-1 ${theme.accent}`}>
                          <TrendingUp className="w-4 h-4" />
                          <span>{translatePhase(conv.current_phase)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats Summary */}
      <motion.div
        className={`${theme.accentBg} rounded-2xl p-6 border ${variant === 'light' ? 'border-[#E02C26]/30' : 'border-[#FCF6BA]/20'}`}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className={`text-3xl font-bold ${theme.accent}`}>
              {Object.keys(conversationsByDate).length}
            </div>
            <div className={`text-sm mt-1 ${theme.muted}`}>{t('calendar.activeDays')}</div>
          </div>
          <div>
            <div className={`text-3xl font-bold ${theme.title}`}>
              {conversations.length}
            </div>
            <div className={`text-sm mt-1 ${theme.muted}`}>{t('calendar.totalSessions')}</div>
          </div>
          <div>
            <div className={`text-3xl font-bold ${theme.accent}`}>
              {conversations.reduce((sum, c) => sum + c.message_count, 0)}
            </div>
            <div className={`text-sm mt-1 ${theme.muted}`}>{t('calendar.totalMessages')}</div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

// Helper function to translate phase names
function translatePhase(phase: string): string {
  const translations: Record<string, string> = {
    'Situation': 'המצוי',
    'Gap': 'הפער',
    'Pattern': 'הדפוס',
    'Paradigm': 'פרדיגמה',
    'Stance': 'עמדה',
    'KMZ': 'כמ"ז',
    'New_Choice': 'בחירה חדשה',
    'Vision': 'חזון',
    'PPD': 'תכנית',
    'S0': 'רשות',
    'S1': 'נושא',
    'S2': 'אירוע',
    'S3': 'רגשות',
    'S4': 'מחשבה',
    'S5': 'מעשה',
    'S6': 'רצוי',
    'S7': 'פער',
    'S8': 'דפוס',
    'S9': 'עמדה',
    'S10': 'כוחות',
    'S11': 'בחירה',
    'S12': 'חזון',
    'S13': 'מחויבות',
  };
  return translations[phase] || phase;
}

