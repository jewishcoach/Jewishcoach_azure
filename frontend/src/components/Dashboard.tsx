import { useState, useEffect } from 'react';
import { useAuth, useUser } from '@clerk/clerk-react';
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

// BSD dashboard (Figma Page 2): cream canvas, slate sidebar, gold accents
const COLORS = {
  bg: '#faf8f3',
  card: '#FFFFFF',
  text: '#393939',
  textMuted: '#8a96a8',
  textOnDarkMuted: 'rgba(255,255,255,0.55)',
  accent: '#1e293b',
  accentLight: 'rgba(30, 41, 59, 0.08)',
  primary: '#2E3A56',
  primaryLight: 'rgba(46, 58, 86, 0.08)',
  gold: '#c8953a',
  goldSoft: '#e4b870',
  goldTintBg: 'rgba(200, 149, 58, 0.1)',
  goldTintBorder: 'rgba(200, 149, 58, 0.22)',
  inputBg: '#fafaf8',
  inputBorder: '#d8d3ca',
  border: '#e8e0cc',
  shadow: '0 2px 16px rgba(0, 0, 0, 0.06)',
  shadowSm: '0 2px 8px rgba(0, 0, 0, 0.06)',
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

/** Plan slug → spaced words for UI (CSS may uppercase). */
function formatPlanWords(plan: string): string {
  return plan.replace(/_/g, ' ').trim();
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

function isLikelyApiNetworkOrTlsError(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false;
  const e = err as { code?: string; message?: string };
  if (e.code === 'ERR_NETWORK') return true;
  const msg = typeof e.message === 'string' ? e.message : '';
  return msg === 'Network Error' || /SSL|ERR_SSL/i.test(msg);
}

export const Dashboard = ({ onBack, onShowBilling }: DashboardProps) => {
  const { getToken } = useAuth();
  const { user } = useUser();
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
    } catch (err: unknown) {
      console.error('Error loading dashboard:', err);
      setData(null);
      setBillingUsage(null);
      const e = err as { response?: { status?: number; data?: { detail?: unknown } }; message?: string };
      const status = e.response?.status;
      const detail = e.response?.data?.detail;
      const detailStr = typeof detail === 'string' ? detail : undefined;
      const fallbackMsg = typeof e.message === 'string' ? e.message : undefined;
      if (status === 401) {
        setError(t('error.reconnect'));
      } else if (isLikelyApiNetworkOrTlsError(err)) {
        setError(t('error.apiUnreachable'));
      } else {
        setError(detailStr || fallbackMsg || t('error.loadData'));
      }
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

  const SubscriptionMeter = () => {
    if (!billingUsage || billingUsage.messages_limit <= 0 || billingUsage.messages_limit === -1) return null;
    const pct = Math.min(
      100,
      Math.round((billingUsage.messages_used / billingUsage.messages_limit) * 100),
    );
    return (
      <div className="mb-1 px-0.5">
        <div className="flex justify-between items-center gap-2 text-[10px] mb-2 font-normal">
          <span style={{ color: COLORS.textOnDarkMuted }}>{t('billing.button')}</span>
          <span className="tabular-nums font-medium" style={{ color: COLORS.gold }} dir="ltr">
            {billingUsage.messages_used} / {billingUsage.messages_limit}
          </span>
        </div>
        <div className="h-1 rounded bg-white/[0.08] overflow-hidden">
          <div
            className="h-full rounded bg-[#c8953a] shadow-[0_0_6px_rgba(212,175,95,0.5)] transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    );
  };

  /** Desktop: vertical links — Figma aside footer */
  const SidebarLinks = () => (
    <div className="flex flex-col gap-6">
      {onShowBilling && (
        <button
          type="button"
          onClick={() => onShowBilling()}
          className="flex items-center gap-3.5 text-start transition-colors hover:text-white/80"
          style={{ color: COLORS.textOnDarkMuted }}
        >
          <CreditCard className="w-4 h-4 shrink-0 opacity-90" strokeWidth={1.75} />
          <span className="text-sm font-normal">{t('billing.button')}</span>
        </button>
      )}
      <button
        type="button"
        onClick={() => setLegalPanel('privacy')}
        className="flex items-center gap-3.5 text-start transition-colors hover:text-white/80"
        style={{ color: COLORS.textOnDarkMuted }}
      >
        <FileText className="w-4 h-4 shrink-0 opacity-90" strokeWidth={1.75} />
        <span className="text-sm font-normal">{t('sidebar.policy')}</span>
      </button>
      <a
        href={BSD_BOOKS_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-start gap-3.5 transition-colors hover:text-white/80"
        style={{ color: COLORS.textMuted }}
      >
        <BookOpen className="w-4 h-4 shrink-0 mt-0.5 opacity-90" strokeWidth={1.75} />
        <span className="text-sm font-normal leading-snug">{t('sidebar.book')}</span>
      </a>
      <button
        type="button"
        onClick={() => setLegalPanel('terms')}
        className="flex items-center gap-3.5 text-start transition-colors hover:text-white/80"
        style={{ color: COLORS.textOnDarkMuted }}
      >
        <Scale className="w-4 h-4 shrink-0 opacity-90" strokeWidth={1.75} />
        <span className="text-sm font-normal">{t('sidebar.terms')}</span>
      </button>
      <a
        href={BSD_WEBSITE_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-4 transition-colors hover:text-white/80"
        style={{ color: COLORS.textMuted }}
      >
        <ExternalLink className="w-3.5 h-3.5 shrink-0 opacity-90" strokeWidth={2} />
        <span className="text-[12.5px] font-normal">bsdcoach.com</span>
      </a>
    </div>
  );

  return (
    <div
      className="flex flex-col md:flex-row h-full overflow-hidden dashboard-container"
      dir={i18n.dir() as 'ltr' | 'rtl'}
      style={{ background: COLORS.bg }}
    >
      {/* Mobile: Sticky top bar — profile name + header links (settings via bottom nav) */}
      <div className="md:hidden sticky top-0 z-10 flex items-center gap-2 px-3 py-2 border-b flex-nowrap min-w-0" style={{ background: COLORS.card, borderColor: COLORS.border, boxShadow: COLORS.shadow }}>
        <div className="min-w-0 flex-1 flex items-center gap-1.5 overflow-hidden">
          <p className="font-semibold truncate text-sm min-w-0" style={{ color: COLORS.text }}>
            {profileHeadingName(profile, t('dashboard.userDefault'))}
          </p>
          <div className="flex items-center gap-1 flex-shrink-0">
            {profile.gender && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium" style={{ background: COLORS.accentLight, color: COLORS.accent }}>
                {profile.gender === 'male' ? t('dashboard.male') : t('dashboard.female')}
              </span>
            )}
            <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium" style={{ background: COLORS.accentLight, color: COLORS.accent }}>
              {formatPlanWords(profile.current_plan).toUpperCase()}
            </span>
          </div>
        </div>
        <HeaderLinks />
      </div>

      {/* Desktop: slate sidebar — Figma Aside */}
      <aside className="hidden md:flex w-[232px] shrink-0 flex-col overflow-y-auto border-e border-white/[0.07] bg-[#1e293b] custom-scrollbar">
        <nav className="flex flex-1 flex-col gap-0 px-4 pb-4 pt-8">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="mb-5 flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors hover:bg-white/[0.06]"
              style={{ color: COLORS.textOnDarkMuted }}
            >
              <MessageCircle className="h-4 w-4 shrink-0" strokeWidth={1.75} />
              {t('chat.button')}
            </button>
          )}
          {NAV_ITEMS.map((item) => (
            <button
              type="button"
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`mb-1 flex w-full items-center gap-3 rounded-[7px] border px-3 py-2.5 text-start text-sm font-normal transition-colors ${
                activeTab === item.id
                  ? 'border-[rgba(200,149,58,0.22)] bg-[rgba(200,149,58,0.1)] text-[#e4b870]'
                  : 'border-transparent text-white/55 hover:bg-white/[0.04]'
              }`}
            >
              <span className="shrink-0 [&_svg]:stroke-[1.75]">{item.icon}</span>
              <span>{t(item.labelKey)}</span>
            </button>
          ))}
        </nav>

        <div className="mt-auto border-t border-white/[0.07] px-4 pb-8 pt-6">
          {billingUsage && billingUsage.messages_limit > 0 && billingUsage.messages_limit !== -1 ? (
            <div className="mb-6 space-y-5">
              <SubscriptionMeter />
              <div className="border-t border-white/[0.07]" aria-hidden />
            </div>
          ) : null}
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
              background: activeTab === item.id ? COLORS.goldTintBg : 'transparent',
              color: activeTab === item.id ? COLORS.gold : COLORS.textMuted,
              border: activeTab === item.id ? `1px solid ${COLORS.goldTintBorder}` : '1px solid transparent',
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
          {/* Profile banner — Figma gradient strip */}
          <motion.div
            className="mb-6 hidden md:block"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div
              className="flex min-h-[122px] items-center gap-6 overflow-hidden rounded-[17px] px-9 py-6 shadow-[0px_2px_16px_rgba(0,0,0,0.06)]"
              style={{
                background: 'linear-gradient(111deg, #2e3a56 0%, #3d5a80 50%, #c9963a 100%)',
              }}
            >
              <div className="relative shrink-0">
                <div
                  className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-full border-[3px] border-[rgba(212,175,95,0.6)] bg-[#2a4a8c] shadow-[0px_8px_32px_rgba(0,0,0,0.3)]"
                  style={{ boxShadow: '0 0 0 6px rgba(212, 175, 95, 0.1), 0 8px 32px rgba(0,0,0,0.3)' }}
                >
                  {user?.imageUrl ? (
                    <img
                      src={user.imageUrl}
                      alt=""
                      className="h-full w-full object-cover object-center"
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <span
                      className="text-[32px] font-bold leading-none text-white"
                      style={{ fontFamily: "'Playfair Display', Georgia, serif" }}
                      aria-hidden
                    >
                      {(profileHeadingName(profile, t('dashboard.userDefault')).trim().charAt(0) || '?').toUpperCase()}
                    </span>
                  )}
                </div>
              </div>
              <div className="min-w-0">
                <p
                  className="text-2xl font-bold leading-tight text-white"
                  style={{ fontFamily: "'Cormorant Garamond', Georgia, serif" }}
                >
                  {profileHeadingName(profile, t('dashboard.userDefault'))}
                </p>
                <div
                  className="mt-3 inline-flex items-center gap-2 rounded-[20px] border border-[rgba(212,175,95,0.3)] bg-[rgba(212,175,95,0.15)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.11em] text-[#e8c97a]"
                >
                  <span className="text-[8px] opacity-90" aria-hidden>
                    ✦
                  </span>
                  <span>{formatPlanWords(profile.current_plan)}</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Tab: Settings — Figma personal settings card */}
          {activeTab === 'settings' && (
            <div className="mx-auto w-full max-w-[632px] space-y-5">
              <motion.div
                className="rounded-2xl bg-white p-6 shadow-[0px_2px_16px_rgba(0,0,0,0.06)] md:p-7"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <h3
                  className="mb-1 text-[22px] font-semibold leading-tight text-[#1e293b]"
                  style={{ fontFamily: "'Playfair Display', Georgia, serif" }}
                >
                  {t('dashboard.title')}
                </h3>
                <p className="mb-6 text-[15px] leading-snug text-[#393939]">{t('dashboard.subtitle')}</p>
                <div className="space-y-5">
                  <div>
                    <label className="mb-2 block text-[14px] font-semibold uppercase tracking-[0.05em] text-[#393939]">
                      {t('dashboard.displayName')}
                    </label>
                    <input
                      type="text"
                      value={editForm.display_name}
                      onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                      placeholder={t('dashboard.displayNamePlaceholder')}
                      className="h-[42px] w-full rounded-[10px] border border-[#d8d3ca] bg-[#fafaf8] px-3.5 text-[14px] text-[#393939] placeholder:text-[#757575] focus:border-[#c8953a]/40 focus:outline-none focus:ring-2 focus:ring-[#c8953a]/15"
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-[14px] font-semibold uppercase tracking-[0.05em] text-[#393939]">
                      {t('dashboard.gender')}
                    </label>
                    <select
                      value={editForm.gender}
                      onChange={(e) => setEditForm({ ...editForm, gender: e.target.value })}
                      className="h-[42px] w-full rounded-[10px] border border-[#d8d3ca] bg-[#fafaf8] px-3.5 text-[14px] text-[#757575] focus:border-[#c8953a]/40 focus:outline-none focus:ring-2 focus:ring-[#c8953a]/15"
                    >
                      <option value="">{t('dashboard.notSpecified')}</option>
                      <option value="male">{t('dashboard.male')}</option>
                      <option value="female">{t('dashboard.female')}</option>
                    </select>
                  </div>
                  <p className="flex gap-2 text-[12px] leading-snug text-[#393939]">
                    <User className="mt-0.5 h-3.5 w-3.5 shrink-0 opacity-70" aria-hidden />
                    <span>{t('dashboard.genderHelp')}</span>
                  </p>
                  <div className="flex flex-wrap justify-end gap-3 pt-1">
                    <button
                      type="button"
                      onClick={revertProfileForm}
                      className="h-[39px] min-w-[96px] rounded-[10px] border border-[#d8d3ca] px-5 text-[14px] text-[#8a96a8] transition-colors hover:bg-[#fafaf8]"
                    >
                      {t('dashboard.cancel')}
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleSaveProfile()}
                      disabled={saving}
                      className="flex h-[39px] min-w-[140px] items-center justify-center gap-2 rounded-[10px] bg-[#1e293b] px-5 text-[13.5px] font-semibold text-[#e8e4dc] transition-opacity disabled:opacity-50"
                    >
                      <Save className="h-3.5 w-3.5" strokeWidth={2} />
                      {saving ? t('dashboard.saving') : t('dashboard.save')}
                    </button>
                  </div>
                </div>
              </motion.div>
              <PwaInstallCard colors={COLORS} />
            </div>
          )}

          {/* Tab: Goals & Reminders */}
          {activeTab === 'goals' && (
            <div className="grid md:grid-cols-2 gap-5">
              <motion.div
                className="rounded-2xl border p-5 md:p-6"
                style={{ background: COLORS.card, borderColor: COLORS.border, boxShadow: COLORS.shadow }}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <GoalsManager variant="light" />
              </motion.div>
              <motion.div
                className="rounded-2xl border p-5 md:p-6"
                style={{ background: COLORS.card, borderColor: COLORS.border, boxShadow: COLORS.shadow }}
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
            <DashboardSupportPanel colors={COLORS} profileEmail={profile.email} refreshAuthToken={getToken} />
          )}

          {/* Tab: History */}
          {activeTab === 'history' && (
            <div className="grid lg:grid-cols-2 gap-6">
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <CoachingCalendar conversations={conversationsForCalendar} variant="light" stats={stats} />
              </motion.div>
              <div className="space-y-6">
                <motion.div
                  className="rounded-2xl border p-5 md:p-6"
                  style={{ background: COLORS.card, borderColor: COLORS.border, boxShadow: COLORS.shadow }}
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
                  className="rounded-2xl border p-5 md:p-6"
                  style={{ background: COLORS.card, borderColor: COLORS.border, boxShadow: COLORS.shadow }}
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
                          className="flex justify-between items-center py-2.5 px-3 rounded-lg transition-colors hover:bg-[#fafaf8]"
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
