import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { SignedIn, SignedOut, UserButton, useUser, useClerk, useAuth } from '@clerk/clerk-react';
import { Shield, BarChart3, Archive, MessageSquarePlus } from 'lucide-react';
import { LanguageSwitcher } from './components/LanguageSwitcher';
import { BSDWorkspace } from './components/workspace/BSDWorkspace';
import { LandingPage } from './components/LandingPage';
import { OnboardingFlow } from './components/OnboardingFlow';
import { hasSeenOnboarding, setOnboardingComplete, clearOnboardingOnSignOut } from './lib/onboardingStorage';
import { AdminDashboard } from './pages/AdminDashboard';
import { BillingPage } from './components/BillingPage';
import { apiClient } from './services/api';
import './i18n';

// Clear onboarding when user is signed out, so next login shows it again
function SignedOutClearOnboarding() {
  useEffect(() => {
    clearOnboardingOnSignOut();
  }, []);
  return null;
}

// Check if running on tunnel domain (Demo Mode)
const isTunnelDomain = () => {
  const hostname = window.location.hostname;
  return hostname.includes('.lhr.life') || 
         hostname.includes('.ngrok-free.app') || 
         hostname.includes('.localhost.run');
};

// Separate component for signed-in content (so useUser is only called when signed in)
function SignedInContent() {
  const { t } = useTranslation();
  const { user } = useUser();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [isAdmin, setIsAdmin] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [showBilling, setShowBilling] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [checkingAdmin, setCheckingAdmin] = useState(true);
  const [displayName, setDisplayName] = useState<string | null>(null);
  /** Incremented from header "new chat" on mobile — BSDWorkspace runs startNewConversation */
  const [workspaceNewChatTick, setWorkspaceNewChatTick] = useState(0);

  const isChatView = !showBilling && !showDashboard && !showAdmin && !checkingAdmin;

  useEffect(() => {
    if (!isLoaded) return;

    if (!isSignedIn) {
      setCheckingAdmin(false);
      return;
    }

    const checkAdminStatus = async () => {
      try {
        const token = await getToken();
        if (token) {
          apiClient.setToken(token);
          const userData = await apiClient.getCurrentUser();
          setIsAdmin(userData.isAdmin);
          setDisplayName(userData.display_name);
          console.log('👤 [App] User data loaded:', {
            display_name: userData.display_name,
            email: userData.email,
            isAdmin: userData.isAdmin
          });
        }
      } catch (error) {
        console.error('Failed to check admin status:', error);
      } finally {
        setCheckingAdmin(false);
      }
    };

    checkAdminStatus();
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
          }
        } catch {
          // Fallback: use Clerk user when API fails (CORS, 401, etc.)
          setDisplayName(user?.firstName ?? null);
        }
      };
      reloadDisplayName();
    }
  }, [showDashboard, showBilling, showAdmin, getToken, user, isLoaded, isSignedIn]);

  return (
    <div className="h-screen flex flex-col bg-[#020617] workspace-root overflow-x-hidden">
      <motion.header
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 120, damping: 14 }}
        className="relative z-20 flex justify-between items-center p-4 md:p-6 bg-[#0f172a] backdrop-blur-[25px] border-b border-white/[0.14] shadow-[0_4px_18px_-2px_rgba(0,0,0,0.45),0_1px_0_0_rgba(255,255,255,0.06)_inset]"
      >
        <div className="flex items-center gap-2 md:gap-[1.2em] flex-shrink-0 min-w-0">
          <img src="/bsd-logo.png" alt="BSD אימון יהודי" className="h-12 md:h-[69px] object-contain flex-shrink-0" />
          <p
            className="text-white font-bold text-base sm:text-lg md:text-[1.8rem] tracking-wide truncate hidden sm:block"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif', lineHeight: 1.4 }}
          >
            אִם יֵשׁ לְךָ שָׁמַיִם, נִתֵּן לְךָ כְּנָפַיִם
          </p>
        </div>
        <div className="flex-1 min-w-2" />
        <div className="flex items-center gap-2 md:gap-4 flex-shrink-0">
          {user && (
            <span className="text-white text-sm md:text-base font-light tracking-[0.02em] hidden sm:inline" style={{ fontFamily: 'Inter, sans-serif' }}>
              {(() => {
                const raw = displayName ?? user?.firstName ?? user?.emailAddresses?.[0]?.emailAddress ?? '';
                const name = (typeof raw === 'string' ? raw : '').replace(/^undefined$/i, '').trim();
                return name ? `${t('app.welcome')}, ${name}!` : `${t('app.welcome')}!`;
              })()}
            </span>
          )}
          {isChatView && (
            <>
              <button
                type="button"
                onClick={() => setArchiveOpen(true)}
                title={t('chat.previousConversationsHint')}
                className="md:hidden inline-flex items-center justify-center rounded-xl min-h-[40px] min-w-[40px] p-0 bg-white border border-[#E2E4E8] text-[#2E3A56] shadow-sm hover:bg-[#F4F6F9] hover:border-[#CCD6E0] transition-colors"
                aria-label={t('chat.previousConversations')}
              >
                <Archive className="w-[18px] h-[18px] text-[#2E3A56]" strokeWidth={2} />
              </button>
              <button
                type="button"
                onClick={() => setWorkspaceNewChatTick((n) => n + 1)}
                title={t('chat.newConversation')}
                className="md:hidden inline-flex items-center justify-center rounded-xl min-h-[40px] min-w-[40px] p-0 shadow-sm transition-all border border-[#FCF6BA]/50 bg-gradient-to-br from-[#BF953F] via-[#FCF6BA] to-[#B38728] text-[#0f172a] hover:brightness-105 hover:border-[#FCF6BA]/80"
                aria-label={t('chat.newConversation')}
              >
                <MessageSquarePlus className="w-[18px] h-[18px] text-[#0f172a]" strokeWidth={2} />
              </button>
            </>
          )}
          <button
            type="button"
            onClick={() => {
              setShowDashboard(!showDashboard);
              setShowBilling(false);
              setShowAdmin(false);
            }}
            title={showDashboard ? t('chat.button') : t('dashboard.button')}
            className="inline-flex items-center justify-center gap-1.5 md:gap-2 px-2 md:px-4 py-2 rounded-xl bg-white border border-[#E2E4E8] text-[#2E3A56] text-xs md:text-sm font-medium shadow-sm hover:bg-[#F4F6F9] hover:border-[#CCD6E0] transition-colors min-h-[40px] min-w-[40px] md:min-h-[44px] md:min-w-0"
            style={{ fontFamily: 'Inter, sans-serif' }}
          >
            <BarChart3 className="w-[18px] h-[18px] md:w-4 md:h-4 flex-shrink-0 text-[#2E3A56]" strokeWidth={2} />
            <span className="hidden md:inline">{showDashboard ? t('chat.button') : t('dashboard.button')}</span>
          </button>
          {isAdmin && !checkingAdmin && (
            <button
              type="button"
              onClick={() => {
                setShowAdmin(!showAdmin);
                setShowBilling(false);
                setShowDashboard(false);
              }}
              title={showAdmin ? t('chat.button') : t('admin.button')}
              className="inline-flex items-center justify-center gap-1.5 md:gap-2 px-2 md:px-4 py-2 rounded-xl bg-white border border-[#E2E4E8] text-[#2E3A56] text-xs md:text-sm font-medium shadow-sm hover:bg-[#F4F6F9] hover:border-[#CCD6E0] transition-colors min-h-[40px] min-w-[40px] md:min-h-[44px] md:min-w-0"
              style={{ fontFamily: 'Inter, sans-serif' }}
            >
              <Shield className="w-[18px] h-[18px] md:w-4 md:h-4 flex-shrink-0 text-[#2E3A56]" strokeWidth={2} />
              <span className="hidden md:inline">{showAdmin ? t('chat.button') : t('admin.button')}</span>
            </button>
          )}
          <LanguageSwitcher />
          <UserButton afterSignOutUrl="/" />
        </div>
      </motion.header>
      <main className="flex-1 flex overflow-hidden">
        {showBilling ? <BillingPage /> : showAdmin ? <AdminDashboard /> : !checkingAdmin && (
          <BSDWorkspace
            displayName={displayName}
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

// Wrapper: show onboarding for first-time users, then main app
function SignedInWithOnboarding() {
  const [showOnboarding, setShowOnboarding] = useState(!hasSeenOnboarding());

  if (showOnboarding) {
    return (
      <OnboardingFlow
        onComplete={() => {
          setOnboardingComplete();
          setShowOnboarding(false);
        }}
      />
    );
  }
  return <SignedInContent />;
}

// Demo Mode Component (for tunnel testing without Clerk)
function DemoModeContent() {
  const { t } = useTranslation();
  const [showDashboard, setShowDashboard] = useState(false);
  const [showBilling, setShowBilling] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(!hasSeenOnboarding());
  const [workspaceNewChatTick, setWorkspaceNewChatTick] = useState(0);
  const isChatView = !showBilling && !showDashboard;

  useEffect(() => {
    // Set demo token for API client (backend will recognize this)
    apiClient.setToken('demo_tunnel_token');
    console.log('🎭 [DEMO MODE] Running in tunnel demo mode - authentication bypassed');
  }, []);

  if (showOnboarding) {
    return (
      <OnboardingFlow
        onComplete={() => {
          setOnboardingComplete();
          setShowOnboarding(false);
        }}
      />
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[#0F172A]">
      <motion.header
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        className="sticky top-0 z-50 flex items-center justify-between p-4 md:p-6 bg-[#0F172A]/95 backdrop-blur-sm border-b border-white/[0.14] shadow-[0_4px_18px_-2px_rgba(0,0,0,0.45),0_1px_0_0_rgba(255,255,255,0.06)_inset]"
      >
        <div className="flex items-center gap-2 md:gap-[1.2em] flex-shrink-0 min-w-0">
          <img src="/bsd-logo.png" alt="BSD אימון יהודי" className="h-12 md:h-[69px] object-contain flex-shrink-0" />
          <p
            className="text-white font-bold text-base sm:text-lg md:text-[1.8rem] tracking-wide truncate hidden sm:block"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif', lineHeight: 1.4 }}
          >
            אִם יֵשׁ לְךָ שָׁמַיִם, נִתֵּן לְךָ כְּנָפַיִם
          </p>
          <span className="px-2 py-1 bg-yellow-500/20 text-yellow-300 text-xs rounded-full border border-yellow-500/30 flex-shrink-0">
            DEMO MODE
          </span>
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-2 md:gap-4 flex-shrink-0">
          {isChatView && (
            <>
              <button
                type="button"
                onClick={() => setArchiveOpen(true)}
                title={t('chat.previousConversationsHint')}
                className="md:hidden inline-flex items-center justify-center rounded-xl min-h-[40px] min-w-[40px] p-0 bg-white border border-[#E2E4E8] text-[#2E3A56] shadow-sm hover:bg-[#F4F6F9] hover:border-[#CCD6E0] transition-colors"
                aria-label={t('chat.previousConversations')}
              >
                <Archive className="w-[18px] h-[18px] text-[#2E3A56]" strokeWidth={2} />
              </button>
              <button
                type="button"
                onClick={() => setWorkspaceNewChatTick((n) => n + 1)}
                title={t('chat.newConversation')}
                className="md:hidden inline-flex items-center justify-center rounded-xl min-h-[40px] min-w-[40px] p-0 shadow-sm transition-all border border-[#FCF6BA]/50 bg-gradient-to-br from-[#BF953F] via-[#FCF6BA] to-[#B38728] text-[#0f172a] hover:brightness-105 hover:border-[#FCF6BA]/80"
                aria-label={t('chat.newConversation')}
              >
                <MessageSquarePlus className="w-[18px] h-[18px] text-[#0f172a]" strokeWidth={2} />
              </button>
            </>
          )}
          <button
            type="button"
            onClick={() => {
              setShowDashboard(!showDashboard);
              setShowBilling(false);
            }}
            title={showDashboard ? t('chat.button') : t('dashboard.button')}
            className="inline-flex items-center justify-center gap-1.5 md:gap-2 px-2 md:px-4 py-2 rounded-xl bg-white border border-[#E2E4E8] text-[#2E3A56] text-xs md:text-sm font-medium shadow-sm hover:bg-[#F4F6F9] hover:border-[#CCD6E0] transition-colors min-h-[40px] min-w-[40px] md:min-h-[44px] md:min-w-0"
            style={{ fontFamily: 'Inter, sans-serif' }}
          >
            <BarChart3 className="w-[18px] h-[18px] md:w-4 md:h-4 flex-shrink-0 text-[#2E3A56]" strokeWidth={2} />
            <span className="hidden md:inline">{showDashboard ? t('chat.button') : t('dashboard.button')}</span>
          </button>
          <LanguageSwitcher />
        </div>
      </motion.header>
      <main className="flex-1 flex overflow-hidden">
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
      {/* Not Signed In - Landing Page. Clear onboarding so next login shows it again. */}
      <SignedOut>
        <SignedOutClearOnboarding />
        <div className="fixed top-4 end-4 z-50">
          <LanguageSwitcher />
        </div>
        <LandingPage onGetStarted={handleGetStarted} />
      </SignedOut>

      {/* Signed In - Onboarding (first time) or Chat Interface */}
      <SignedIn>
        <SignedInWithOnboarding />
      </SignedIn>
    </>
  );
}

export default App;
