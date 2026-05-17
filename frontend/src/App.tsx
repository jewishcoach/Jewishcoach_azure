import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { SignedIn, SignedOut, useUser, useClerk, useAuth } from '@clerk/clerk-react';
import { Shield, LayoutDashboard, MessageCircle, MessageSquarePlus } from 'lucide-react';
import { LanguageSwitcher } from './components/LanguageSwitcher';
import { BSDWorkspace } from './components/workspace/BSDWorkspace';
import { LandingPage } from './components/LandingPage';
import { BsdOnboardingFlow } from './components/BsdOnboardingFlow';
import { AppUserButton } from './components/AppUserButton';
import { AdminDashboard } from './pages/AdminDashboard';
import { BillingPage } from './components/BillingPage';
import { apiClient } from './services/api';
import './i18n';
import { isClerkSyntheticEmail } from './lib/clerkEmail';
import { isClerkUiAdminAllowlisted } from './config';
import { normalizeTraineeGender } from './utils/welcomeMessage';

// Check if running on tunnel domain (Demo Mode)
const isTunnelDomain = () => {
  const hostname = window.location.hostname;
  return hostname.includes('.lhr.life') || 
         hostname.includes('.ngrok-free.app') || 
         hostname.includes('.localhost.run');
};

type ChatHeaderMobileControlsProps = {
  isChatView: boolean;
  showDashboard: boolean;
  onNewConversation: () => void;
  onToggleDashboard: () => void;
  /** Workspace TOPBAR (Figma BSD frame): slate pills instead of white tiles */
  headerTheme?: 'light' | 'dark';
};

/** Icon + tiny label under each action — md+ unchanged text beside dashboard only */
function ChatHeaderMobileControls({
  isChatView,
  showDashboard,
  onNewConversation,
  onToggleDashboard,
  headerTheme = 'light',
}: ChatHeaderMobileControlsProps) {
  const { t } = useTranslation();
  const tile =
    'flex flex-col items-center justify-center gap-0.5 rounded-xl px-1 py-1 min-h-[52px] min-w-[58px] max-w-[76px]';
  const dashCls =
    headerTheme === 'dark'
      ? 'inline-flex flex-col md:flex-row items-center justify-center gap-0.5 md:gap-2 px-1 md:px-4 py-1 md:py-2 rounded-xl border border-white/[0.11] bg-[#1c2333] text-[#e8e4dc] min-h-[52px] min-w-[58px] max-w-[76px] md:max-w-none md:min-h-[44px] md:min-w-0 text-xs md:text-sm font-light hover:bg-[#252d42] transition-colors'
      : 'inline-flex flex-col md:flex-row items-center justify-center gap-0.5 md:gap-2 px-1 md:px-4 py-1 md:py-2 rounded-xl bg-white border border-[#E2E4E8] text-[#2E3A56] shadow-sm hover:bg-[#F4F6F9] hover:border-[#CCD6E0] transition-colors min-h-[52px] min-w-[58px] max-w-[76px] md:max-w-none md:min-h-[44px] md:min-w-0 text-xs md:text-sm font-medium';

  return (
    <>
      {isChatView && (
        <>
          <button
            type="button"
            onClick={onNewConversation}
            title={t('chat.newConversation')}
            aria-label={t('chat.newConversation')}
            className={`${tile} md:hidden shadow-sm transition-all border border-[#FCF6BA]/50 bg-gradient-to-br from-[#BF953F] via-[#FCF6BA] to-[#B38728] hover:brightness-105 hover:border-[#FCF6BA]/80`}
          >
            <MessageSquarePlus className="w-[18px] h-[18px] flex-shrink-0 text-[#0f172a]" strokeWidth={2} />
            <span className="text-[8px] font-semibold leading-[1.15] text-center text-[#0f172a] px-0.5">
              {t('chat.mobileHeader.newChat')}
            </span>
          </button>
        </>
      )}
      <button
        type="button"
        onClick={onToggleDashboard}
        title={showDashboard ? t('chat.button') : t('dashboard.button')}
        aria-label={showDashboard ? t('chat.button') : t('dashboard.button')}
        className={dashCls}
        style={{ fontFamily: 'Inter, sans-serif' }}
      >
        {showDashboard ? (
          <MessageCircle
            className={`w-[18px] h-[18px] md:w-4 md:h-4 flex-shrink-0 ${headerTheme === 'dark' ? 'text-[#e8e4dc]' : 'text-[#2E3A56]'}`}
            strokeWidth={2}
          />
        ) : (
          <LayoutDashboard
            className={`w-[18px] h-[18px] md:w-4 md:h-4 flex-shrink-0 ${headerTheme === 'dark' ? 'text-[#e8e4dc]' : 'text-[#2E3A56]'}`}
            strokeWidth={2}
          />
        )}
        <span
          className={`md:hidden text-[8px] font-semibold leading-[1.15] text-center px-0.5 ${headerTheme === 'dark' ? 'text-[#e8e4dc]' : ''}`}
        >
          {showDashboard ? t('chat.mobileHeader.backToChat') : t('chat.mobileHeader.personal')}
        </span>
        <span className={`hidden md:inline ${headerTheme === 'dark' ? 'font-light' : ''}`}>
          {showDashboard ? t('chat.button') : t('dashboard.button')}
        </span>
      </button>
    </>
  );
}

// Separate component for signed-in content (so useUser is only called when signed in)
function SignedInContent() {
  const { t, i18n } = useTranslation();
  const { user } = useUser();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [isAdmin, setIsAdmin] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [showBilling, setShowBilling] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [profileGender, setProfileGender] = useState<ReturnType<typeof normalizeTraineeGender>>(null);
  /** After first /users/me attempt — delays chat welcome until profile display_name can override Clerk */
  const [chatProfileReady, setChatProfileReady] = useState(false);
  /** First-session onboarding until preferences flag is set */
  const [showIntroScreens, setShowIntroScreens] = useState(false);
  /** False until /users/me/preferences resolved — avoids flashing workspace chat before onboarding */
  const [introPrefsResolved, setIntroPrefsResolved] = useState(false);
  /** Incremented from header "new chat" on mobile — BSDWorkspace runs startNewConversation */
  const [workspaceNewChatTick, setWorkspaceNewChatTick] = useState(0);

  const adminUiAllowlisted = isClerkUiAdminAllowlisted(user?.id);
  const showAdminChrome = isAdmin || adminUiAllowlisted;

  const isChatView = !showBilling && !showDashboard && !showAdmin;

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;

    const checkAdminStatus = async (isRetry = false) => {
      try {
        const token = await getToken();
        if (token) {
          apiClient.setToken(token);
          const userData = await apiClient.getCurrentUser();
          setIsAdmin(!!userData.isAdmin);
          setDisplayName(userData.display_name);
          setProfileGender(normalizeTraineeGender(userData.gender));
          try {
            const prefs = await apiClient.getUserPreferences();
            setShowIntroScreens(!prefs?.bsd_intro_screens_completed);
          } catch {
            setShowIntroScreens(false);
          }
          setIntroPrefsResolved(true);
          if (!userData.isAdmin && !isRetry) {
            window.setTimeout(() => {
              void checkAdminStatus(true);
            }, 2000);
          }
        } else {
          setIsAdmin(false);
          setDisplayName(null);
          setProfileGender(null);
          setShowIntroScreens(false);
          setIntroPrefsResolved(true);
        }
      } catch (error) {
        console.error('Failed to check admin status:', error);
        setShowIntroScreens(false);
        setIntroPrefsResolved(true);
        if (!isRetry) {
          window.setTimeout(() => {
            void checkAdminStatus(true);
          }, 2000);
        }
      } finally {
        setChatProfileReady(true);
      }
    };

    void checkAdminStatus();
  }, [isLoaded, isSignedIn, getToken]);

  // Reload display name when returning from dashboard
  useEffect(() => {
    if (!showDashboard && !showBilling && !showAdmin) {
      const reloadDisplayName = async () => {
        if (!isLoaded || !isSignedIn) return;
        try {
          const token = await getToken();
          if (token) {
            apiClient.setToken(token);
            const userData = await apiClient.getCurrentUser();
            setDisplayName(userData?.display_name ?? user?.firstName ?? null);
            setProfileGender(normalizeTraineeGender(userData?.gender));
          }
        } catch {
          // Fallback: use Clerk user when API fails (CORS, 401, etc.)
          setDisplayName(user?.firstName ?? null);
          setProfileGender(null);
        }
      };
      reloadDisplayName();
    }
  }, [showDashboard, showBilling, showAdmin, getToken, user, isLoaded, isSignedIn]);

  const handleIntroComplete = useCallback(async () => {
    try {
      const token = await getToken();
      if (token) {
        apiClient.setToken(token);
        await apiClient.patchUserPreferences({ bsd_intro_screens_completed: true });
        const userData = await apiClient.getCurrentUser();
        setDisplayName(userData.display_name ?? null);
        setProfileGender(normalizeTraineeGender(userData.gender));
      }
    } catch (e) {
      console.warn('[BsdOnboardingFlow] Failed to persist completion:', e);
    }
    setShowIntroScreens(false);
  }, [getToken]);

  if (!isLoaded || !introPrefsResolved) {
    return (
      <div
        className="h-screen flex flex-col items-center justify-center bg-[#faf8f3] workspace-root overflow-x-hidden"
        role="status"
        aria-busy="true"
        aria-live="polite"
      >
        <div className="flex flex-col items-center gap-3">
          <div
            className="h-9 w-9 animate-spin rounded-full border-2 border-[#C9A96E] border-t-transparent"
            aria-hidden
          />
          <p className="text-sm text-[#4c5a70]" style={{ fontFamily: 'Inter, sans-serif' }}>
            {t('chat.loading')}
          </p>
        </div>
      </div>
    );
  }

  if (showIntroScreens) {
    return (
      <div className="h-screen flex flex-col bg-[#faf8f3] workspace-root overflow-x-hidden">
        <BsdOnboardingFlow
          onComplete={handleIntroComplete}
          initialDisplayName={displayName ?? null}
          onDisplayNameUpdated={(name) => setDisplayName(name)}
        />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-[#faf8f3] workspace-root overflow-x-hidden">
      <motion.header
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 120, damping: 14 }}
        className="relative z-20 flex min-h-[66px] justify-between items-center p-4 md:p-6 bg-[#1e293b] backdrop-blur-[25px] border-b border-white/[0.07] shadow-[0_4px_18px_-2px_rgba(0,0,0,0.35)]"
      >
        <div className="flex items-center gap-2 md:gap-[1.2em] flex-shrink-0 min-w-0">
          <img src="/bsd-logo.png" alt="BSD אימון יהודי" className="h-12 md:h-[69px] object-contain flex-shrink-0" />
          <p
            className="text-[#f0f4fa] font-semibold text-base sm:text-lg md:text-[1.75rem] tracking-[0.02em] truncate hidden sm:block"
            dir={i18n.language.startsWith('he') ? 'rtl' : 'ltr'}
            style={{
              fontFamily: i18n.language.startsWith('he')
                ? '"Frank Ruhl Libre", "Heebo", serif'
                : '"Cormorant Garamond", Georgia, "Times New Roman", serif',
              lineHeight: 1.35,
              fontWeight: 600,
            }}
          >
            {t('app.headerTagline')}
          </p>
        </div>
        <div className="flex-1 min-w-2" />
        <div className="flex items-center gap-2 md:gap-4 flex-shrink-0">
          {user && (
            <span
              className="hidden sm:inline text-sm md:text-base font-light tracking-[0.02em]"
              style={{ fontFamily: 'Inter, sans-serif' }}
            >
              {(() => {
                const clerkPrimary = user?.emailAddresses?.[0]?.emailAddress;
                const raw =
                  displayName ??
                  user?.firstName ??
                  (clerkPrimary && !isClerkSyntheticEmail(clerkPrimary) ? clerkPrimary : '');
                const name = (typeof raw === 'string' ? raw : '').replace(/^undefined$/i, '').trim();
                return name ? (
                  <>
                    <span className="text-[#8b97ae]">{t('app.welcome')}, </span>
                    <span className="text-[#c8953a]">{name}</span>
                    <span className="text-[#8b97ae]">!</span>
                  </>
                ) : (
                  <span className="text-[#8b97ae]">{t('app.welcome')}!</span>
                );
              })()}
            </span>
          )}
          <ChatHeaderMobileControls
            isChatView={isChatView}
            showDashboard={showDashboard}
            headerTheme="dark"
            onNewConversation={() => setWorkspaceNewChatTick((n) => n + 1)}
            onToggleDashboard={() => {
              setShowDashboard(!showDashboard);
              setShowBilling(false);
              setShowAdmin(false);
            }}
          />
          {showAdminChrome && (
            <button
              type="button"
              onClick={() => {
                setShowAdmin(!showAdmin);
                setShowBilling(false);
                setShowDashboard(false);
              }}
              title={showAdmin ? t('chat.button') : t('admin.button')}
              className="inline-flex items-center justify-center gap-1.5 md:gap-2 px-2 md:px-4 py-2 rounded-xl border border-white/[0.11] bg-[#1c2333] text-[#e8e4dc] text-xs md:text-sm font-light hover:bg-[#252d42] transition-colors min-h-[40px] min-w-[40px] md:min-h-[44px] md:min-w-0"
              style={{ fontFamily: 'Inter, sans-serif' }}
            >
              <Shield className="w-[18px] h-[18px] md:w-4 md:h-4 flex-shrink-0 text-[#e8e4dc]" strokeWidth={2} />
              <span className="hidden md:inline">{showAdmin ? t('chat.button') : t('admin.button')}</span>
            </button>
          )}
          <LanguageSwitcher variant="dark" />
          <AppUserButton />
        </div>
      </motion.header>
      <main
        className={
          showBilling || showAdmin
            ? 'flex-1 min-h-0 overflow-auto overscroll-contain'
            : 'flex-1 flex min-h-0 overflow-hidden'
        }
      >
        {showBilling ? <BillingPage /> : showAdmin ? <AdminDashboard /> : (
          <BSDWorkspace
            displayName={displayName}
            profileGender={profileGender}
            chatProfileReady={chatProfileReady}
            showDashboard={showDashboard}
            onCloseDashboard={() => setShowDashboard(false)}
            onShowBilling={() => {
              setShowBilling(true);
              setShowDashboard(false);
            }}
            archiveOpen={archiveOpen}
            onArchiveOpenChange={setArchiveOpen}
            headerNewChatTick={workspaceNewChatTick}
          />
        )}
      </main>
    </div>
  );
}

// Demo Mode Component (for tunnel testing without Clerk)
function DemoModeContent() {
  const { t, i18n } = useTranslation();
  const [showDashboard, setShowDashboard] = useState(false);
  const [showBilling, setShowBilling] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [workspaceNewChatTick, setWorkspaceNewChatTick] = useState(0);
  const isChatView = !showBilling && !showDashboard;

  useEffect(() => {
    // Set demo token for API client (backend will recognize this)
    apiClient.setToken('demo_tunnel_token');
    console.log('🎭 [DEMO MODE] Running in tunnel demo mode - authentication bypassed');
  }, []);

  return (
    <div className="flex flex-col h-screen bg-[#faf8f3]">
      <motion.header
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        className="sticky top-0 z-50 flex min-h-[66px] items-center justify-between p-4 md:p-6 bg-[#1e293b] backdrop-blur-sm border-b border-white/[0.07] shadow-[0_4px_18px_-2px_rgba(0,0,0,0.35)]"
      >
        <div className="flex items-center gap-2 md:gap-[1.2em] flex-shrink-0 min-w-0">
          <img src="/bsd-logo.png" alt="BSD אימון יהודי" className="h-12 md:h-[69px] object-contain flex-shrink-0" />
          <p
            className="text-[#f0f4fa] font-semibold text-base sm:text-lg md:text-[1.75rem] tracking-[0.02em] truncate hidden sm:block"
            dir={i18n.language.startsWith('he') ? 'rtl' : 'ltr'}
            style={{
              fontFamily: i18n.language.startsWith('he')
                ? '"Frank Ruhl Libre", "Heebo", serif'
                : '"Cormorant Garamond", Georgia, "Times New Roman", serif',
              lineHeight: 1.35,
              fontWeight: 600,
            }}
          >
            {t('app.headerTagline')}
          </p>
          <span className="px-2 py-1 bg-yellow-500/20 text-yellow-300 text-xs rounded-full border border-yellow-500/30 flex-shrink-0">
            DEMO MODE
          </span>
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-2 md:gap-4 flex-shrink-0">
          <ChatHeaderMobileControls
            isChatView={isChatView}
            showDashboard={showDashboard}
            headerTheme="dark"
            onNewConversation={() => setWorkspaceNewChatTick((n) => n + 1)}
            onToggleDashboard={() => {
              setShowDashboard(!showDashboard);
              setShowBilling(false);
            }}
          />
          <LanguageSwitcher variant="dark" />
        </div>
      </motion.header>
      <main
        className={
          showBilling
            ? 'flex-1 min-h-0 overflow-auto overscroll-contain'
            : 'flex-1 flex min-h-0 overflow-hidden'
        }
      >
        {showBilling ? <BillingPage /> : (
          <BSDWorkspace
            displayName="Demo User"
            showDashboard={showDashboard}
            onCloseDashboard={() => setShowDashboard(false)}
            onShowBilling={() => {
              setShowBilling(true);
              setShowDashboard(false);
            }}
            archiveOpen={archiveOpen}
            onArchiveOpenChange={setArchiveOpen}
            headerNewChatTick={workspaceNewChatTick}
          />
        )}
      </main>
    </div>
  );
}

function App() {
  const { openSignIn } = useClerk();

  const handleGetStarted = () => {
    openSignIn({
      afterSignInUrl: '/',
      afterSignUpUrl: '/',
    });
  };

  // Check if running in demo mode (tunnel domain)
  const demoMode = isTunnelDomain();

  if (demoMode) {
    return <DemoModeContent />;
  }

  return (
    <>
      <SignedOut>
        <>
          <div className="fixed top-4 end-4 z-50">
            <LanguageSwitcher />
          </div>
          <LandingPage onGetStarted={handleGetStarted} />
        </>
      </SignedOut>

      <SignedIn>
        <SignedInContent />
      </SignedIn>
    </>
  );
}

export default App;
