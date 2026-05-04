import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import {
  User, Settings, Save, Target, History,
  Loader2, CreditCard, FileText, ExternalLink, BookOpen,
  ScanEye, Scale, MessageCircle, LifeBuoy,
} from 'lucide-react';
import { CoachingCalendar } from './CoachingCalendar';
import { RemindersManager } from './RemindersManager';
import { GoalsManager } from './GoalsManager';
import { PhaseDonutChart } from './dashboard/PhaseDonutChart';
import { DashboardSupportPanel } from './dashboard/DashboardSupportPanel';
import { InsightsTab } from './InsightsTab';
import { PrivacyPolicyPage } from './PrivacyPolicyPage';
import { TermsOfUsePage } from './TermsOfUsePage';
import { PwaInstallCard } from './PwaInstallCard';
import { apiClient } from '../services/api';
import type { I18nT } from '../i18nT';
import { friendlyEmailPrefix, isClerkSyntheticEmail } from '../lib/clerkEmail';

// BSD palette: navy primary, minimal red - gold for soft accents
const COLORS = {
  bg: '#F0F1F3',
  card: '#FFFFFF',
  text: '#2E3A56',
  textMuted: '#5A6B8A',
  accent: '#2E3A56',
  accentLight: 'rgba(46, 58, 86, 0.12)',
  primary: '#2E3A56',
  primaryLight: 'rgba(46, 58, 86, 0.08)',
  gold: '#B38728',
  border: '#E2E4E8',
  shadow: '0 1px 2px rgba(46, 58, 86, 0.06)',
  shadowSm: '0 2px 8px rgba(46, 58, 86, 0.08)',
};

interface Profile {
  id: number;
  email: string | null;
  display_name: string | null;
  gender: string | null;
  is_admin: boolean;
  current_plan: string;
  created_at: string;
}

function profileHeadingName(profile: Profile, defaultLabel: string): string {
  const dn = profile.display_name?.trim();
  if (dn) return dn;
  const fromEmail = friendlyEmailPrefix(profile.email);
  if (fromEmail) return fromEmail;
  return defaultLabel;
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
  /** All conversations for calendar markers (recent_conversations may be truncated). */
  calendar_conversations?: any[];
}

interface DashboardProps {
  onBack?: () => void;
  onShowBilling?: () => void;
}

type DashboardTab = 'settings' | 'goals' | 'history' | 'insights' | 'support';

type LegalPanel = null | 'privacy' | 'terms';

const NAV_ITEMS: { id: DashboardTab; labelKey: string; icon: React.ReactNode }[] = [
  { id: 'settings', labelKey: 'dashboard.tab.settings', icon: <Settings className="w-5 h-5" /> },
  { id: 'goals', labelKey: 'dashboard.tab.goalsReminders', icon: <Target className="w-5 h-5" /> },
  { id: 'history', labelKey: 'dashboard.tab.history', icon: <History className="w-5 h-5" /> },
  { id: 'insights', labelKey: 'dashboard.tab.insights', icon: <ScanEye className="w-5 h-5" /> },
  { id: 'support', labelKey: 'dashboard.tab.support', icon: <LifeBuoy className="w-5 h-5" /> },
];

const BSD_WEBSITE_URL = 'https://bsdcoach.com';
const BSD_BOOKS_URL = 'https://bsdcoach.com/post/the-books';

export const Dashboard = ({ onBack, onShowBilling }: DashboardProps) => {
  const { getToken } = useAuth();
  const { t, i18n } = useTranslation();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ display_name: '', gender: '' });
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<DashboardTab>('settings');
  const [legalPanel, setLegalPanel] = useState<LegalPanel>(null);
  const [billingUsage, setBillingUsage] = useState<{
    messages_used: number;
    messages_limit: number;
  } | null>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setError(null);
    setLoading(true);
    try {
      const token = await getToken();
      if (!token && !apiClient.getToken()) {
        setError(t('error.reconnect'));
        setData(null);
        setBillingUsage(null);
        return;
      }
      if (token) apiClient.setToken(token);
      const [dashboardData, billingOverview] = await Promise.all([
        apiClient.getDashboard(),
        apiClient.getBillingOverview().catch(() => null),
      ]);
      if (billingOverview?.usage) {
        setBillingUsage({
          messages_used: billingOverview.usage.messages_used,
          messages_limit: billingOverview.usage.messages_limit,
        });
      } else {
        setBillingUsage(null);
      }
      if (dashboardData?.profile && dashboardData?.stats) {
        setData(dashboardData);
        setEditForm({
          display_name: dashboardData.profile.display_name || '',
          gender: dashboardData.profile.gender || ''
        });
      } else {
        setData(null);
        setError(t('error.loadData'));
      }
    } catch (err: any) {
      console.error('Error loading dashboard:', err);
      setData(null);
      setBillingUsage(null);
      const status = err?.response?.status;
      const msg = err?.response?.data?.detail || err?.message;
      setError(status === 401 ? t('error.reconnect') : msg || t('error.loadData'));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      await apiClient.updateProfile(editForm);
      await loadDashboard();
    } catch (error) {
      console.error('Error saving profile:', error);
    } finally {
      setSaving(false);
    }
  };

  if (legalPanel === 'privacy') {
    return <PrivacyPolicyPage onBack={() => setLegalPanel(null)} />;
  }
  if (legalPanel === 'terms') {
    return <TermsOfUsePage onBack={() => setLegalPanel(null)} />;
  }

  if (loading) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center" style={{ background: COLORS.bg }}>
        <div className="flex flex-col items-center justify-center gap-3">
          <Loader2 className="h-12 w-12 animate-spin" style={{ color: COLORS.accent }} />
          <p className="text-sm" style={{ color: COLORS.textMuted }}>{t('chat.loading')}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 p-8" style={{ background: COLORS.bg, color: COLORS.text }}>
        <p>{error || t('error.loadData')}</p>
        {onBack && (
          <button
            onClick={() => { setError(null); loadDashboard(); }}
            className="px-4 py-2 rounded-xl text-sm font-medium transition-colors"
            style={{ background: COLORS.accent, color: '#fff' }}
          >
            {t('error.tryAgain')}
          </button>
        )}
        {onBack && (
          <button onClick={onBack} className="text-sm" style={{ color: COLORS.textMuted }}>
            {t('error.back')}
          </button>
        )}
      </div>
    );
  }

  const { profile, stats, recent_conversations, calendar_conversations } = data;
  const conversationsForCalendar =
    calendar_conversations && calendar_conversations.length > 0
      ? calendar_conversations
      : recent_conversations;
  if (!profile || !stats) {
    return (
      <div className="flex-1 flex items-center justify-center p-8" style={{ background: COLORS.bg, color: COLORS.text }}>
        שגיאה בנתונים – נסה שוב
      </div>
    );
  }

  const revertProfileForm = () => {
    setEditForm({
      display_name: profile.display_name || '',
      gender: profile.gender || '',
    });
  };

  /** Mobile: horizontal compact links in header */
  const HeaderLinks = () => (
    <div className="flex items-center gap-1 md:gap-2 flex-nowrap flex-shrink-0">
      {onShowBilling && (
        <button
          onClick={() => onShowBilling()}
          className="flex items-center gap-1 px-1.5 py-1 md:px-2 md:py-1.5 rounded-lg transition-colors hover:bg-gray-100 whitespace-nowrap min-w-0"
          style={{ color: COLORS.textMuted }}
          aria-label={t('billing.button')}
        >
          <CreditCard className="w-4 h-4 flex-shrink-0" />
          <span className="text-[9px] md:text-sm truncate" dir="auto">
            {t('billing.button.short')}
          </span>
        </button>
      )}
      <button
        type="button"
        onClick={() => setLegalPanel('privacy')}
        className="flex items-center gap-1 px-1.5 py-1 md:px-2 md:py-1.5 rounded-lg transition-colors hover:bg-gray-100 whitespace-nowrap min-w-0"
        style={{ color: COLORS.textMuted }}
        aria-label={t('sidebar.policy')}
      >
        <FileText className="w-4 h-4 flex-shrink-0" />
        <span className="text-[9px] md:text-sm truncate">{t('sidebar.policy.short')}</span>
      </button>
      <a
        href={BSD_BOOKS_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1 px-1.5 py-1 md:px-2 md:py-1.5 rounded-lg transition-colors hover:bg-gray-100 whitespace-nowrap min-w-0"
        style={{ color: COLORS.textMuted }}
        aria-label={t('sidebar.book')}
      >
        <BookOpen className="w-4 h-4 flex-shrink-0" />
        <span className="text-[9px] md:text-sm truncate">{t('sidebar.book.short')}</span>
      </a>
      <button
        type="button"
        onClick={() => setLegalPanel('terms')}
        className="flex items-center gap-1 px-1.5 py-1 md:px-2 md:py-1.5 rounded-lg transition-colors hover:bg-gray-100 whitespace-nowrap min-w-0"
        style={{ color: COLORS.textMuted }}
        aria-label={t('sidebar.terms')}
      >
        <Scale className="w-4 h-4 flex-shrink-0" />
        <span className="text-[9px] md:text-sm truncate">{t('sidebar.terms.short')}</span>
      </button>
    </div>
  );

  /** Desktop: vertical links at bottom of sidebar (original placement) */
  const SidebarLinks = () => (
    <div className="flex flex-col gap-1">
      {onShowBilling && (
        <button
          onClick={() => onShowBilling()}
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium w-full transition-colors hover:bg-gray-50 text-start"
          style={{ color: COLORS.textMuted }}
        >
          <CreditCard className="w-4 h-4 flex-shrink-0" />
          <span className="flex flex-col items-start leading-tight">
            <span>{t('billing.button')}</span>
            {billingUsage && billingUsage.messages_limit !== -1 ? (
              <span className="text-xs font-normal opacity-80 mt-0.5" dir="ltr">
                {billingUsage.messages_used}/{billingUsage.messages_limit}
              </span>
            ) : null}
          </span>
        </button>
      )}
      <button
        type="button"
        onClick={() => setLegalPanel('privacy')}
        className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium w-full transition-colors hover:bg-gray-50 text-start"
        style={{ color: COLORS.textMuted }}
      >
        <FileText className="w-4 h-4 flex-shrink-0" />
        {t('sidebar.policy')}
      </button>
      <a
        href={BSD_BOOKS_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium w-full transition-colors hover:bg-gray-50"
        style={{ color: COLORS.textMuted }}
      >
        <BookOpen className="w-4 h-4 flex-shrink-0" />
        {t('sidebar.book')}
      </a>
      <button
        type="button"
        onClick={() => setLegalPanel('terms')}
        className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium w-full transition-colors hover:bg-gray-50 text-start"
        style={{ color: COLORS.textMuted }}
      >
        <Scale className="w-4 h-4 flex-shrink-0" />
        {t('sidebar.terms')}
      </button>
      <a
        href={BSD_WEBSITE_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium w-full transition-colors hover:bg-gray-50"
        style={{ color: COLORS.textMuted }}
      >
        <ExternalLink className="w-4 h-4 flex-shrink-0" />
        {t('sidebar.website')}
      </a>
    </div>
  );

  return (
    <div
      className="flex flex-col md:flex-row h-full overflow-hidden dashboard-container"
      dir={i18n.dir() as 'ltr' | 'rtl'}
      style={{ background: COLORS.bg }}
    >
      {/* Mobile: Sticky top bar - one row: settings | profile | header links */}
      <div className="md:hidden sticky top-0 z-10 flex items-center gap-2 px-3 py-2 border-b flex-nowrap min-w-0" style={{ background: COLORS.card, borderColor: COLORS.border, boxShadow: COLORS.shadow }}>
        <button
          type="button"
          onClick={() => setActiveTab('settings')}
          className="p-1.5 rounded-lg transition-colors hover:bg-gray-100 flex-shrink-0"
          style={{ color: COLORS.textMuted }}
          title={t('dashboard.tab.settings')}
          aria-label={t('dashboard.tab.settings')}
        >
          <Settings className="w-5 h-5" />
        </button>
        <div className="min-w-0 flex-1 flex items-center gap-1.5 overflow-hidden">
          <p className="font-semibold truncate text-sm" style={{ color: COLORS.text }}>
            {profileHeadingName(profile, t('dashboard.userDefault'))}
          </p>
          <div className="flex items-center gap-1 flex-shrink-0">
            {profile.gender && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium" style={{ background: COLORS.accentLight, color: COLORS.accent }}>
                {profile.gender === 'male' ? t('dashboard.male') : t('dashboard.female')}
              </span>
            )}
            <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium" style={{ background: COLORS.accentLight, color: COLORS.accent }}>
              {profile.current_plan.toUpperCase()}
            </span>
          </div>
        </div>
        <HeaderLinks />
      </div>

      {/* Desktop: Left Sidebar */}
      <aside className="hidden md:flex w-56 flex-shrink-0 flex-col py-6 px-3" style={{ background: COLORS.card, boxShadow: COLORS.shadow }}>
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-3 py-2 mb-4 rounded-xl text-sm transition-colors hover:bg-gray-50"
            style={{ color: COLORS.textMuted }}
          >
            <MessageCircle className="w-4 h-4 flex-shrink-0" />
            {t('chat.button')}
          </button>
        )}
        <nav className="flex flex-col gap-1 flex-1">
          {NAV_ITEMS.map((item) => (
            <button
              type="button"
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all text-start w-full"
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
        <div className="mt-auto pt-4 border-t" style={{ borderColor: COLORS.border }}>
          <SidebarLinks />
        </div>
      </aside>

      {/* Mobile: Bottom tab bar */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-10 flex items-center justify-around py-2 px-2"
        style={{
          background: COLORS.card,
          borderTop: `1px solid ${COLORS.border}`,
          boxShadow: '0 -2px 10px rgba(0,0,0,0.06)',
          paddingBottom: 'max(0.5rem, env(safe-area-inset-bottom))',
        }}
      >
        {NAV_ITEMS.map((item) => (
          <button
            type="button"
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className="flex flex-col items-center justify-center gap-1 px-4 py-2 rounded-xl min-w-[64px] transition-all"
            style={{
              background: activeTab === item.id ? COLORS.accentLight : 'transparent',
              color: activeTab === item.id ? COLORS.accent : COLORS.textMuted,
            }}
          >
            {item.icon}
            <span className="text-[11px] font-medium">{t(item.labelKey)}</span>
          </button>
        ))}
      </nav>

      {/* Main Content - pb for mobile bottom nav */}
      <main className="flex-1 overflow-y-auto custom-scrollbar pb-24 md:pb-0">
        <div className="max-w-4xl mx-auto px-4 md:px-6 py-6 md:py-8 overflow-x-hidden">
          {/* Hero Banner - desktop only; mobile has compact top bar */}
          <motion.div
            className="relative rounded-2xl overflow-hidden mb-6 hidden md:block"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ boxShadow: COLORS.shadowSm }}
          >
            <div
              className="h-36 w-full"
              style={{
                background: `linear-gradient(135deg, ${COLORS.primaryLight} 0%, ${COLORS.primary} 60%, ${COLORS.gold} 100%)`,
              }}
            />
            <div className="absolute bottom-0 right-1/2 translate-x-1/2 translate-y-1/2">
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center border-4"
                style={{ background: COLORS.card, borderColor: COLORS.card, boxShadow: COLORS.shadowSm }}
              >
                <User className="w-10 h-10" style={{ color: COLORS.gold }} />
              </div>
            </div>
          </motion.div>

          {/* Profile + Stats row - desktop only */}
          <motion.div
            className="text-center mb-8 hidden md:block"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.05 }}
          >
            <h1
              className={`text-xl font-semibold ${profile.email && !isClerkSyntheticEmail(profile.email) ? 'mb-0.5' : 'mb-5'}`}
              style={{ color: COLORS.text }}
            >
              {profileHeadingName(profile, t('dashboard.userDefault'))}
            </h1>
            {profile.email && !isClerkSyntheticEmail(profile.email) && (
              <p className="text-sm mb-5" style={{ color: COLORS.textMuted }}>
                {profile.email}
              </p>
            )}

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

          {/* Tab: Settings — personal profile only (open card) */}
          {activeTab === 'settings' && (
            <div className="max-w-xl w-full mx-auto space-y-5">
              <motion.div
                className="rounded-xl p-5 md:p-6"
                style={{ background: COLORS.card, boxShadow: COLORS.shadow }}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <h3 className="text-base font-semibold mb-1" style={{ color: COLORS.text }}>{t('dashboard.title')}</h3>
                <p className="text-xs leading-snug mb-5" style={{ color: COLORS.textMuted }}>{t('dashboard.subtitle')}</p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium mb-1.5" style={{ color: COLORS.textMuted }}>{t('dashboard.displayName')}</label>
                    <input
                      type="text"
                      value={editForm.display_name}
                      onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                      className="w-full px-3 py-2.5 text-sm rounded-lg border focus:ring-2 focus:ring-blue-200 focus:outline-none"
                      style={{ borderColor: COLORS.border, color: COLORS.text }}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium mb-1.5" style={{ color: COLORS.textMuted }}>{t('dashboard.gender')}</label>
                    <select
                      value={editForm.gender}
                      onChange={(e) => setEditForm({ ...editForm, gender: e.target.value })}
                      className="w-full px-3 py-2 text-[13px] leading-snug rounded-lg border focus:ring-2 focus:ring-blue-200 focus:outline-none"
                      style={{ borderColor: COLORS.border, color: COLORS.text }}
                    >
                      <option value="">{t('dashboard.notSpecified')}</option>
                      <option value="male">{t('dashboard.male')}</option>
                      <option value="female">{t('dashboard.female')}</option>
                    </select>
                  </div>
                  <div className="flex flex-wrap gap-2 justify-end pt-1">
                    <button
                      type="button"
                      onClick={handleSaveProfile}
                      disabled={saving}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg text-white disabled:opacity-50"
                      style={{ background: COLORS.accent }}
                    >
                      <Save className="w-4 h-4" />
                      {saving ? t('dashboard.saving') : t('dashboard.save')}
                    </button>
                    <button
                      type="button"
                      onClick={revertProfileForm}
                      className="px-4 py-2.5 text-sm rounded-lg"
                      style={{ background: COLORS.border, color: COLORS.text }}
                    >
                      {t('dashboard.cancel')}
                    </button>
                  </div>
                  <p className="text-xs pt-1" style={{ color: COLORS.textMuted }}>{t('dashboard.genderHelp')}</p>
                </div>
              </motion.div>
              <PwaInstallCard colors={COLORS} />
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

          {/* Tab: Insights */}
          {activeTab === 'insights' && <InsightsTab />}

          {/* Tab: Support */}
          {activeTab === 'support' && (
            <DashboardSupportPanel colors={COLORS} profileEmail={profile.email} />
          )}

          {/* Tab: History */}
          {activeTab === 'history' && (
            <div className="grid lg:grid-cols-2 gap-6">
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <CoachingCalendar conversations={conversationsForCalendar} variant="light" stats={stats} />
              </motion.div>
              <div className="space-y-6">
                <motion.div
                  className="rounded-xl p-5"
                  style={{ background: COLORS.card, boxShadow: COLORS.shadow }}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <h3 className="text-base font-semibold mb-4" style={{ color: COLORS.text }}>{t('dashboard.phaseDistribution')}</h3>
                  {conversationsForCalendar.length > 0 ? (
                    <PhaseDonutChart
                      conversationsLabel={t('dashboard.conversations')}
                      data={phaseDistributionFromConversations(conversationsForCalendar, t)}
                    />
                  ) : (
                    <div className="flex items-center justify-center py-12 text-sm" style={{ color: COLORS.textMuted }}>
                      {t('dashboard.noConversations')}
                    </div>
                  )}
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
                              {t('dashboard.convMessages', { count: conv.message_count })} • {translatePhase(conv.current_phase, t)}
                            </div>
                          </div>
                          <div className="text-xs" style={{ color: COLORS.textMuted }}>
                            {new Date(conv.created_at).toLocaleDateString(i18n.language === 'he' ? 'he-IL' : 'en-US')}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </motion.div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

function phaseDistributionFromConversations(
  conversations: { current_phase?: string | null }[],
  t: I18nT
): { phase: string; label: string; count: number }[] {
  const byPhase: Record<string, number> = {};
  conversations.forEach((c) => {
    const p = c.current_phase || 'S0';
    byPhase[p] = (byPhase[p] || 0) + 1;
  });
  return Object.entries(byPhase)
    .map(([phase, count]) => ({ phase, label: translatePhase(phase, t), count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);
}

function translatePhase(phase: string, t: I18nT): string {
  const key = `phase.${phase}`;
  const translated = String(t(key));
  return translated !== key ? translated : phase;
}
