import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import {
  User, Award, Settings, Save, X, ArrowRight, Target, History,
  MessageSquare, Calendar, TrendingUp
} from 'lucide-react';
import { CoachingCalendar } from './CoachingCalendar';
import { RemindersManager } from './RemindersManager';
import { GoalsManager } from './GoalsManager';
import { ActivityBarChart } from './dashboard/ActivityBarChart';
import { PhaseDonutChart } from './dashboard/PhaseDonutChart';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// BSD Logo palette: dark blue #2E3A56, light gray #EBEBEB, red accent #E02C26
const COLORS = {
  bg: '#F0F1F3',
  card: '#FFFFFF',
  text: '#2E3A56',
  textMuted: '#5A6B8A',
  accent: '#E02C26',
  accentLight: 'rgba(224, 44, 38, 0.12)',
  primary: '#2E3A56',
  primaryLight: 'rgba(46, 58, 86, 0.08)',
  border: '#E2E4E8',
  shadow: '0 1px 2px rgba(46, 58, 86, 0.06)',
  shadowSm: '0 2px 8px rgba(46, 58, 86, 0.08)',
};

interface Profile {
  id: number;
  email: string;
  display_name: string | null;
  gender: string | null;
  is_admin: boolean;
  current_plan: string;
  created_at: string;
}

interface DashboardStats {
  total_conversations: number;
  total_messages: number;
  current_phase: string | null;
  days_active: number;
  messages_this_month: number;
  longest_conversation_messages: number;
  favorite_coaching_phase: string | null;
}

interface DashboardData {
  profile: Profile;
  stats: DashboardStats;
  recent_conversations: any[];
}

interface DashboardProps {
  onBack?: () => void;
}

type DashboardTab = 'summary' | 'goals' | 'history';

const NAV_ITEMS: { id: DashboardTab; labelKey: string; icon: React.ReactNode }[] = [
  { id: 'summary', labelKey: 'dashboard.tab.summary', icon: <User className="w-5 h-5" /> },
  { id: 'goals', labelKey: 'dashboard.tab.goalsReminders', icon: <Target className="w-5 h-5" /> },
  { id: 'history', labelKey: 'dashboard.tab.history', icon: <History className="w-5 h-5" /> },
];

export const Dashboard = ({ onBack }: DashboardProps) => {
  const { getToken } = useAuth();
  const { t, i18n } = useTranslation();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ display_name: '', gender: '' });
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<DashboardTab>('summary');

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/profile/dashboard`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const dashboardData = await response.json();
      setData(dashboardData);
      setEditForm({
        display_name: dashboardData.profile.display_name || '',
        gender: dashboardData.profile.gender || ''
      });
    } catch (error) {
      console.error('Error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      const token = await getToken();
      await fetch(`${API_URL}/profile/me`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm)
      });
      await loadDashboard();
      setEditing(false);
    } catch (error) {
      console.error('Error saving profile:', error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ background: COLORS.bg }}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-t-transparent mx-auto" style={{ borderColor: COLORS.accent }} />
          <p className="mt-3 text-sm" style={{ color: COLORS.textMuted }}>טוען נתונים...</p>
        </div>
      </div>
    );
  }

  if (!data) return <div className="flex-1 flex items-center justify-center p-8" style={{ background: COLORS.bg, color: COLORS.text }}>שגיאה בטעינת נתונים</div>;

  const { profile, stats, recent_conversations } = data;
  const isNewUser = stats.total_conversations === 0;

  return (
    <div className="flex h-full overflow-hidden dashboard-container" dir="rtl" style={{ background: COLORS.bg }}>
      {/* Left Sidebar - MatDash style */}
      <aside className="w-56 flex-shrink-0 flex flex-col py-6 px-3" style={{ background: COLORS.card, boxShadow: COLORS.shadow }}>
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-3 py-2 mb-4 rounded-xl text-sm transition-colors hover:bg-gray-50"
            style={{ color: COLORS.textMuted }}
          >
            <ArrowRight className="w-4 h-4" />
            {t('chat.button')}
          </button>
        )}
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all"
              style={{
                background: activeTab === item.id ? COLORS.accent : 'transparent',
                color: activeTab === item.id ? '#FFFFFF' : COLORS.textMuted,
              }}
            >
              {item.icon}
              {t(item.labelKey)}
            </button>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="max-w-4xl mx-auto px-6 py-8">
          {/* Hero Banner */}
          <motion.div
            className="relative rounded-2xl overflow-hidden mb-6"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ boxShadow: COLORS.shadowSm }}
          >
            <div
              className="h-36 w-full"
              style={{
                background: `linear-gradient(135deg, ${COLORS.primaryLight} 0%, ${COLORS.primary} 40%, ${COLORS.accent} 100%)`,
              }}
            />
            <div className="absolute bottom-0 right-1/2 translate-x-1/2 translate-y-1/2">
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center border-4"
                style={{ background: COLORS.card, borderColor: COLORS.card, boxShadow: COLORS.shadowSm }}
              >
                <User className="w-10 h-10" style={{ color: COLORS.accent }} />
              </div>
            </div>
          </motion.div>

          {/* Profile + Stats row - Instagram style */}
          <motion.div
            className="text-center mb-8"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.05 }}
          >
            <h1 className="text-xl font-semibold mb-0.5" style={{ color: COLORS.text }}>
              {profile.display_name || profile.email?.split('@')[0] || 'משתמש'}
            </h1>
            <p className="text-sm mb-5" style={{ color: COLORS.textMuted }}>{profile.email}</p>

            {/* Stats - horizontal, minimal */}
            <div className="flex justify-center gap-12 mb-5">
              <div className="text-center">
                <div className="text-xl font-semibold" style={{ color: COLORS.text }}>{stats.total_conversations}</div>
                <div className="text-xs" style={{ color: COLORS.textMuted }}>{t('dashboard.conversations')}</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-semibold" style={{ color: COLORS.text }}>{stats.total_messages}</div>
                <div className="text-xs" style={{ color: COLORS.textMuted }}>{t('dashboard.messages')}</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-semibold" style={{ color: COLORS.text }}>{stats.days_active}</div>
                <div className="text-xs" style={{ color: COLORS.textMuted }}>{t('dashboard.daysActive')}</div>
              </div>
            </div>

            {/* Badges */}
            <div className="flex flex-wrap justify-center gap-2">
              {profile.gender && (
                <span className="text-xs px-2.5 py-1 rounded-full" style={{ background: COLORS.accentLight, color: COLORS.accent }}>
                  {profile.gender === 'male' ? t('dashboard.male') : t('dashboard.female')}
                </span>
              )}
              <span className="text-xs px-2.5 py-1 rounded-full font-medium" style={{ background: COLORS.accentLight, color: COLORS.accent }}>
                {profile.current_plan.toUpperCase()}
              </span>
            </div>
          </motion.div>

          {/* Tab: Summary */}
          {activeTab === 'summary' && (
            <div className="space-y-6">
              {isNewUser && (
                <motion.div
                  className="rounded-xl py-4 px-5 text-center"
                  style={{ background: COLORS.accentLight }}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <p className="text-sm" style={{ color: COLORS.text }}>{t('dashboard.newUserWelcome')}</p>
                </motion.div>
              )}

              {/* Charts row */}
              <div className="grid md:grid-cols-2 gap-5">
                <motion.div
                  className="rounded-xl p-5"
                  style={{ background: COLORS.card, boxShadow: COLORS.shadow }}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <h3 className="text-base font-semibold mb-4" style={{ color: COLORS.text }}>{t('dashboard.stats')}</h3>
                  <ActivityBarChart
                    data={[
                      { label: t('dashboard.conversations'), value: stats.total_conversations, max: 10 },
                      { label: t('dashboard.messages'), value: stats.total_messages, max: 50 },
                      { label: t('dashboard.daysActive'), value: stats.days_active, max: 30 },
                      { label: t('dashboard.thisMonth'), value: stats.messages_this_month, max: 50 },
                    ]}
                  />
                </motion.div>
                <motion.div
                  className="rounded-xl p-5"
                  style={{ background: COLORS.card, boxShadow: COLORS.shadow }}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 }}
                >
                  <h3 className="text-base font-semibold mb-4" style={{ color: COLORS.text }}>התפלגות שלבים</h3>
                  {recent_conversations.length > 0 ? (
                    <PhaseDonutChart
                      data={(() => {
                        const byPhase: Record<string, number> = {};
                        recent_conversations.forEach((c) => {
                          const p = c.current_phase || 'S0';
                          byPhase[p] = (byPhase[p] || 0) + 1;
                        });
                        return Object.entries(byPhase)
                          .map(([phase, count]) => ({ phase, label: translatePhase(phase), count }))
                          .sort((a, b) => b.count - a.count)
                          .slice(0, 6);
                      })()}
                    />
                  ) : (
                    <div className="flex items-center justify-center py-12 text-sm" style={{ color: COLORS.textMuted }}>
                      אין עדיין שיחות
                    </div>
                  )}
                </motion.div>
              </div>

              {/* Two-column content cards */}
              <div className="grid md:grid-cols-2 gap-5">
                {/* Profile / Edit card */}
                <motion.div
                  className="rounded-xl p-5"
                  style={{ background: COLORS.card, boxShadow: COLORS.shadow }}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-base font-semibold" style={{ color: COLORS.text }}>{t('dashboard.title')}</h3>
                    <button
                      onClick={() => setEditing(!editing)}
                      className="p-1.5 rounded-lg transition-colors hover:bg-gray-100"
                      style={{ color: COLORS.textMuted }}
                    >
                      {editing ? <X className="w-4 h-4" /> : <Settings className="w-4 h-4" />}
                    </button>
                  </div>
                  {editing ? (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
                      <div>
                        <label className="block text-xs font-medium mb-1.5" style={{ color: COLORS.textMuted }}>{t('dashboard.displayName')}</label>
                        <input
                          type="text"
                          value={editForm.display_name}
                          onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                          className="w-full px-3 py-2 text-sm rounded-lg border focus:ring-2 focus:ring-blue-200 focus:outline-none"
                          style={{ borderColor: COLORS.border, color: COLORS.text }}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium mb-1.5" style={{ color: COLORS.textMuted }}>{t('dashboard.gender')}</label>
                        <select
                          value={editForm.gender}
                          onChange={(e) => setEditForm({ ...editForm, gender: e.target.value })}
                          className="w-full px-3 py-2 text-sm rounded-lg border focus:ring-2 focus:ring-blue-200 focus:outline-none"
                          style={{ borderColor: COLORS.border, color: COLORS.text }}
                        >
                          <option value="">{t('dashboard.notSpecified')}</option>
                          <option value="male">{t('dashboard.male')}</option>
                          <option value="female">{t('dashboard.female')}</option>
                        </select>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={handleSaveProfile}
                          disabled={saving}
                          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg text-white disabled:opacity-50"
                          style={{ background: COLORS.accent }}
                        >
                          <Save className="w-4 h-4" />
                          {saving ? t('dashboard.saving') : t('dashboard.save')}
                        </button>
                        <button
                          onClick={() => setEditing(false)}
                          className="px-4 py-2 text-sm rounded-lg"
                          style={{ background: COLORS.border, color: COLORS.text }}
                        >
                          {t('dashboard.cancel')}
                        </button>
                      </div>
                      <p className="text-xs" style={{ color: COLORS.textMuted }}>{t('dashboard.genderHelp')}</p>
                    </motion.div>
                  ) : (
                    <p className="text-sm" style={{ color: COLORS.textMuted }}>
                      {profile.display_name || profile.email}
                    </p>
                  )}
                </motion.div>

                {/* Journey card */}
                <motion.div
                  className="rounded-xl p-5"
                  style={{ background: COLORS.card, boxShadow: COLORS.shadow }}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 }}
                >
                  <h3 className="text-base font-semibold mb-4" style={{ color: COLORS.text }}>{t('dashboard.journey')}</h3>
                  <div className="space-y-2.5 text-sm">
                    {stats.current_phase && (
                      <div className="flex justify-between">
                        <span style={{ color: COLORS.textMuted }}>{t('dashboard.currentStage')}</span>
                        <span className="font-medium" style={{ color: COLORS.accent }}>{translatePhase(stats.current_phase)}</span>
                      </div>
                    )}
                    {stats.favorite_coaching_phase && (
                      <div className="flex justify-between">
                        <span style={{ color: COLORS.textMuted }}>{t('dashboard.favoriteStage')}</span>
                        <span className="font-medium" style={{ color: COLORS.text }}>{translatePhase(stats.favorite_coaching_phase)}</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span style={{ color: COLORS.textMuted }}>{t('dashboard.longestConversation')}</span>
                      <span className="font-medium" style={{ color: COLORS.text }}>{stats.longest_conversation_messages} {t('dashboard.messagesCount')}</span>
                    </div>
                  </div>
                </motion.div>

                {/* Achievements - full width, icons only */}
                <motion.div
                  className="md:col-span-2 rounded-xl p-5"
                  style={{ background: COLORS.card, boxShadow: COLORS.shadow }}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  <h3 className="text-base font-semibold mb-4 flex items-center gap-2" style={{ color: COLORS.text }}>
                    <Award className="w-4 h-4" style={{ color: COLORS.accent }} />
                    {t('dashboard.achievements')}
                  </h3>
                  <div className="flex flex-wrap gap-4">
                    {stats.total_conversations >= 5 && <AchievementBadge icon={<MessageSquare className="w-4 h-4" />} text={t('dashboard.achievement5Conversations')} />}
                    {stats.total_messages >= 50 && <AchievementBadge icon={<MessageSquare className="w-4 h-4" />} text={t('dashboard.achievement50Messages')} />}
                    {stats.days_active >= 7 && <AchievementBadge icon={<Calendar className="w-4 h-4" />} text={t('dashboard.achievement7Days')} />}
                    {stats.longest_conversation_messages >= 20 && <AchievementBadge icon={<TrendingUp className="w-4 h-4" />} text={t('dashboard.achievement20Messages')} />}
                    {stats.total_conversations < 5 && stats.total_messages < 50 && stats.days_active < 7 && stats.longest_conversation_messages < 20 && (
                      <p className="text-sm italic" style={{ color: COLORS.textMuted }}>{t('dashboard.noAchievements')}</p>
                    )}
                  </div>
                </motion.div>
              </div>
            </div>
          )}

          {/* Tab: Goals & Reminders */}
          {activeTab === 'goals' && (
            <div className="grid md:grid-cols-2 gap-5">
              <motion.div
                className="rounded-xl p-5"
                style={{ background: COLORS.card, boxShadow: COLORS.shadow }}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <GoalsManager variant="light" />
              </motion.div>
              <motion.div
                className="rounded-xl p-5"
                style={{ background: COLORS.card, boxShadow: COLORS.shadow }}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
              >
                <RemindersManager variant="light" />
              </motion.div>
            </div>
          )}

          {/* Tab: History */}
          {activeTab === 'history' && (
            <div className="grid lg:grid-cols-2 gap-6">
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <CoachingCalendar conversations={recent_conversations} variant="light" />
              </motion.div>
              <motion.div
                className="rounded-xl p-5"
                style={{ background: COLORS.card, boxShadow: COLORS.shadow }}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <h3 className="text-base font-semibold mb-4" style={{ color: COLORS.text }}>{t('dashboard.recentConversations')}</h3>
                {recent_conversations.length === 0 ? (
                  <p className="text-center py-8 text-sm" style={{ color: COLORS.textMuted }}>{t('dashboard.noConversations')}</p>
                ) : (
                  <div className="space-y-2">
                    {recent_conversations.slice(0, 10).map((conv) => (
                      <div
                        key={conv.id}
                        className="flex justify-between items-center py-2.5 px-3 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <div>
                          <div className="text-sm font-medium" style={{ color: COLORS.text }}>{conv.title}</div>
                          <div className="text-xs" style={{ color: COLORS.textMuted }}>
                            {conv.message_count} הודעות • {translatePhase(conv.current_phase)}
                          </div>
                        </div>
                        <div className="text-xs" style={{ color: COLORS.textMuted }}>
                          {new Date(conv.created_at).toLocaleDateString('he-IL')}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

function AchievementBadge({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ background: COLORS.accentLight, color: COLORS.accent }}>
      {icon}
      <span className="text-sm" style={{ color: COLORS.text }}>{text}</span>
    </div>
  );
}

function translatePhase(phase: string): string {
  const translations: Record<string, string> = {
    'Situation': 'המצוי', 'Gap': 'הפער', 'Pattern': 'הדפוס', 'Paradigm': 'פרדיגמה',
    'Stance': 'עמדה', 'KMZ': 'כמ"ז', 'New_Choice': 'בחירה חדשה', 'Vision': 'חזון', 'PPD': 'תכנית',
    'S0': 'רשות', 'S1': 'נושא', 'S2': 'אירוע', 'S3': 'רגשות', 'S4': 'מחשבה', 'S5': 'מעשה',
    'S6': 'רצוי', 'S7': 'פער', 'S8': 'דפוס', 'S9': 'עמדה', 'S10': 'כוחות', 'S11': 'בחירה',
    'S12': 'חזון', 'S13': 'מחויבות',
  };
  return translations[phase] || phase;
}
