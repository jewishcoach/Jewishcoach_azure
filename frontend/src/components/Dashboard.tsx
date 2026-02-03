import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { 
  User, MessageSquare, TrendingUp, Calendar, Award,
  Settings, Edit2, Save, X
} from 'lucide-react';
import { CoachingCalendar } from './CoachingCalendar';
import { RemindersManager } from './RemindersManager';
import { GoalsManager } from './GoalsManager';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

export const Dashboard = () => {
  const { getToken } = useAuth();
  const { t, i18n } = useTranslation();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ display_name: '', gender: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/profile/dashboard`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
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
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
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
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto"></div>
          <p className="mt-4 text-gray-600">טוען נתונים...</p>
        </div>
      </div>
    );
  }

  if (!data) return <div>שגיאה בטעינת נתונים</div>;

  const { profile, stats, recent_conversations } = data;

  return (
    <div className="flex-1 w-full bg-gradient-to-br from-blue-50 via-white to-purple-50 overflow-y-auto" dir="rtl">
      <div className="max-w-7xl mx-auto p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-primary mb-2">{t('dashboard.title')}</h1>
          <p className="text-gray-600">{t('dashboard.subtitle')}</p>
        </div>

        {/* Profile Card */}
        <motion.div
          className="bg-white rounded-2xl p-6 shadow-lg mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-accent to-primary flex items-center justify-center">
                <User className="w-8 h-8 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">
                  {profile.display_name || profile.email?.split('@')[0] || 'משתמש'}
                </h2>
                <p className="text-gray-600">{profile.email}</p>
                <div className="flex gap-2 mt-1">
                  {profile.gender && (
                    <span className="text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      {profile.gender === 'male' ? `👨 ${t('dashboard.male')}` : `👩 ${t('dashboard.female')}`}
                    </span>
                  )}
                  <span className="text-sm bg-accent/20 text-accent px-2 py-1 rounded font-bold">
                    {profile.current_plan.toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={() => setEditing(!editing)}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              {editing ? <X className="w-5 h-5" /> : <Settings className="w-5 h-5" />}
            </button>
          </div>

          {/* Edit Profile Form */}
          {editing && (
            <motion.div
              className="border-t pt-4 mt-4"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
            >
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">{t('dashboard.displayName')}</label>
                  <input
                    type="text"
                    value={editForm.display_name}
                    onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                    placeholder={t('dashboard.displayName')}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-accent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">{t('dashboard.gender')}</label>
                  <select
                    value={editForm.gender}
                    onChange={(e) => setEditForm({ ...editForm, gender: e.target.value })}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-accent"
                  >
                    <option value="">{t('dashboard.notSpecified')}</option>
                    <option value="male">{t('dashboard.male')}</option>
                    <option value="female">{t('dashboard.female')}</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <button
                  onClick={handleSaveProfile}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-dark transition-colors disabled:opacity-50"
                >
                  <Save className="w-4 h-4" />
                  {saving ? t('dashboard.saving') : t('dashboard.save')}
                </button>
                <button
                  onClick={() => setEditing(false)}
                  className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  {t('dashboard.cancel')}
                </button>
              </div>
              <p className="text-sm text-gray-600 mt-3">
                {t('dashboard.genderHelp')}
              </p>
            </motion.div>
          )}
        </motion.div>

        {/* Stats Grid */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <StatCard
            icon={<MessageSquare className="w-6 h-6" />}
            title={t('dashboard.conversations')}
            value={stats.total_conversations}
            color="blue"
          />
          <StatCard
            icon={<MessageSquare className="w-6 h-6" />}
            title={t('dashboard.messages')}
            value={stats.total_messages}
            color="green"
          />
          <StatCard
            icon={<Calendar className="w-6 h-6" />}
            title={t('dashboard.daysActive')}
            value={stats.days_active}
            color="purple"
          />
          <StatCard
            icon={<TrendingUp className="w-6 h-6" />}
            title={t('dashboard.thisMonth')}
            value={stats.messages_this_month}
            color="orange"
          />
        </div>

        {/* Additional Stats */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <motion.div
            className="bg-white rounded-2xl p-6 shadow-lg"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h3 className="text-lg font-bold mb-4">{t('dashboard.journey')}</h3>
            <div className="space-y-3">
              {stats.current_phase && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">{t('dashboard.currentStage')}</span>
                  <span className="font-bold text-accent">{translatePhase(stats.current_phase)}</span>
                </div>
              )}
              {stats.favorite_coaching_phase && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">{t('dashboard.favoriteStage')}</span>
                  <span className="font-bold">{translatePhase(stats.favorite_coaching_phase)}</span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-gray-600">{t('dashboard.longestConversation')}</span>
                <span className="font-bold">{stats.longest_conversation_messages} {t('dashboard.messagesCount')}</span>
              </div>
            </div>
          </motion.div>

          <motion.div
            className="bg-white rounded-2xl p-6 shadow-lg"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Award className="w-5 h-5 text-yellow-500" />
              {t('dashboard.achievements')}
            </h3>
            <div className="space-y-2">
              {stats.total_conversations >= 5 && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-2xl">🎯</span>
                  <span>{t('dashboard.achievement5Conversations')}</span>
                </div>
              )}
              {stats.total_messages >= 50 && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-2xl">💬</span>
                  <span>{t('dashboard.achievement50Messages')}</span>
                </div>
              )}
              {stats.days_active >= 7 && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-2xl">📅</span>
                  <span>{t('dashboard.achievement7Days')}</span>
                </div>
              )}
              {stats.longest_conversation_messages >= 20 && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-2xl">🏆</span>
                  <span>{t('dashboard.achievement20Messages')}</span>
                </div>
              )}
            </div>
          </motion.div>
        </div>

        {/* Calendar Section with Goals & Reminders */}
        <div className="grid lg:grid-cols-2 gap-8 mb-8">
          {/* Left Column: Calendar + Recent Conversations */}
          <div className="space-y-6">
            {recent_conversations.length > 0 && (
              <CoachingCalendar conversations={recent_conversations} />
            )}
            
            {/* Recent Conversations */}
            <motion.div
              className="bg-white rounded-2xl p-6 shadow-lg"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <h3 className="text-lg font-bold mb-4">{t('dashboard.recentConversations')}</h3>
              {recent_conversations.length === 0 ? (
                <p className="text-gray-500 text-center py-4">{t('dashboard.noConversations')}</p>
              ) : (
                <div className="space-y-2">
                  {recent_conversations.slice(0, 5).map((conv) => (
                    <div
                      key={conv.id}
                      className="flex justify-between items-center p-3 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div>
                        <div className="font-medium">{conv.title}</div>
                        <div className="text-sm text-gray-600">
                          {conv.message_count} הודעות • {translatePhase(conv.current_phase)}
                        </div>
                      </div>
                      <div className="text-sm text-gray-500">
                        {new Date(conv.created_at).toLocaleDateString('he-IL')}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </div>

          {/* Right Column: Goals & Reminders */}
          <div className="space-y-6">
            <motion.div
              className="bg-white rounded-2xl p-6 shadow-lg"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <GoalsManager />
            </motion.div>

            <motion.div
              className="bg-white rounded-2xl p-6 shadow-lg"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
            >
              <RemindersManager />
            </motion.div>
          </div>
        </div>

      </div>
    </div>
  );
};

// Helper Component
interface StatCardProps {
  icon: React.ReactNode;
  title: string;
  value: number;
  color: 'blue' | 'green' | 'purple' | 'orange';
}

const StatCard = ({ icon, title, value, color }: StatCardProps) => {
  const colorClasses = {
    blue: 'from-blue-500 to-blue-600',
    green: 'from-green-500 to-green-600',
    purple: 'from-purple-500 to-purple-600',
    orange: 'from-orange-500 to-orange-600',
  };

  return (
    <motion.div
      className="bg-white rounded-2xl p-6 shadow-lg"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.05 }}
    >
      <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${colorClasses[color]} flex items-center justify-center text-white mb-3`}>
        {icon}
      </div>
      <div className="text-3xl font-bold mb-1">{value}</div>
      <div className="text-gray-600 text-sm">{title}</div>
    </motion.div>
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
    'PPD': 'תכנית'
  };
  return translations[phase] || phase;
}

