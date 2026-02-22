import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { SignedIn, SignedOut, UserButton, useUser, useClerk, useAuth } from '@clerk/clerk-react';
import { Sparkles, Shield, CreditCard, BarChart3 } from 'lucide-react';
import { LanguageSwitcher } from './components/LanguageSwitcher';
import { BSDWorkspace } from './components/workspace/BSDWorkspace';
import { LandingPage } from './components/LandingPage';
import { AdminDashboard } from './pages/AdminDashboard';
import { BillingPageSimple as BillingPage } from './components/BillingPageSimple';
import { Dashboard } from './components/Dashboard';
import { apiClient } from './services/api';
import './i18n';

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
  const { getToken } = useAuth();
  const [isAdmin, setIsAdmin] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [showBilling, setShowBilling] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [checkingAdmin, setCheckingAdmin] = useState(true);
  const [displayName, setDisplayName] = useState<string | null>(null);

  useEffect(() => {
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
  }, [getToken]);

  // Reload display name when returning from dashboard
  useEffect(() => {
    if (!showDashboard && !showBilling && !showAdmin) {
      const reloadDisplayName = async () => {
        try {
          const token = await getToken();
          if (token) {
            apiClient.setToken(token);
            const userData = await apiClient.getCurrentUser();
            setDisplayName(userData.display_name);
          }
        } catch (error) {
          console.error('Failed to reload display name:', error);
        }
      };
      reloadDisplayName();
    }
  }, [showDashboard, showBilling, showAdmin, getToken]);

  return (
    <div className="h-screen flex flex-col bg-[#020617] workspace-root">
      <motion.header
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 120, damping: 14 }}
        className="relative z-20 flex justify-between items-center p-6 bg-[#020617]/95 backdrop-blur-[25px] border-b border-white/[0.08]"
      >
        <h1 className="text-xl font-light text-white flex items-center gap-2 tracking-[0.1em]" style={{ fontFamily: 'Cormorant Garamond, Playfair Display, serif' }}>
          <Sparkles className="w-5 h-5" style={{ filter: 'drop-shadow(0 0 6px rgba(212, 175, 55, 0.5))', color: '#FCF6BA' }} />
          {t('app.title')}
        </h1>
        <div className="flex items-center gap-4">
          {user && (
            <span className="text-white/80 text-sm font-light tracking-[0.02em]" style={{ fontFamily: 'Inter, sans-serif' }}>
              {t('app.welcome')}, {displayName || user.firstName || user.emailAddresses[0].emailAddress}!
            </span>
          )}
          <button
            onClick={() => {
              setShowDashboard(!showDashboard);
              setShowBilling(false);
              setShowAdmin(false);
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-[4px] bg-white/[0.06] hover:bg-white/[0.1] text-white text-sm font-light transition-colors"
            style={{ fontFamily: 'Inter, sans-serif' }}
          >
            <BarChart3 className="w-4 h-4" />
            {showDashboard ? t('chat.button') : t('dashboard.button')}
          </button>
          <button
            onClick={() => {
              setShowBilling(!showBilling);
              setShowDashboard(false);
              setShowAdmin(false);
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-[4px] text-sm font-light transition-colors"
            style={{ background: 'rgba(212,175,55,0.12)', color: '#FCF6BA', fontFamily: 'Inter, sans-serif' }}
          >
            <CreditCard className="w-4 h-4" />
            {showBilling ? t('chat.button') : t('billing.button')}
          </button>
          {isAdmin && !checkingAdmin && (
            <button
              onClick={() => {
                setShowAdmin(!showAdmin);
                setShowBilling(false);
                setShowDashboard(false);
              }}
              className="flex items-center gap-2 px-4 py-2 rounded-[4px] bg-white/[0.06] hover:bg-white/[0.1] text-white text-sm font-light transition-colors"
              style={{ fontFamily: 'Inter, sans-serif' }}
            >
              <Shield className="w-4 h-4" />
              {showAdmin ? t('chat.button') : t('admin.button')}
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
          />
        )}
      </main>
    </div>
  );
}

// Demo Mode Component (for tunnel testing without Clerk)
function DemoModeContent() {
  const { t } = useTranslation();
  const [showDashboard, setShowDashboard] = useState(false);
  const [showBilling, setShowBilling] = useState(false);

  useEffect(() => {
    // Set demo token for API client (backend will recognize this)
    apiClient.setToken('demo_tunnel_token');
    console.log('🎭 [DEMO MODE] Running in tunnel demo mode - authentication bypassed');
  }, []);

  return (
    <div className="flex flex-col h-screen bg-[#0F172A]">
      <motion.header
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        className="sticky top-0 z-50 flex items-center justify-between p-4 bg-[#0F172A]/95 backdrop-blur-sm border-b border-white/10"
      >
        <div className="flex items-center gap-3">
          <Sparkles className="w-8 h-8 text-accent" />
          <h1 className="text-2xl font-bold text-white">{t('app.title')}</h1>
          <span className="px-2 py-1 bg-yellow-500/20 text-yellow-300 text-xs rounded-full border border-yellow-500/30">
            DEMO MODE
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setShowDashboard(!showDashboard);
              setShowBilling(false);
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
          >
            <BarChart3 className="w-4 h-4" />
            {showDashboard ? t('chat.button') : t('dashboard.button')}
          </button>
          <button
            onClick={() => {
              setShowBilling(!showBilling);
              setShowDashboard(false);
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
          >
            <CreditCard className="w-4 h-4" />
            {showBilling ? t('chat.button') : t('billing.button')}
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
      {/* Not Signed In - Landing Page */}
      <SignedOut>
        <div className="fixed top-4 end-4 z-50">
          <LanguageSwitcher />
        </div>
        <LandingPage onGetStarted={handleGetStarted} />
      </SignedOut>

      {/* Signed In - Chat Interface */}
      <SignedIn>
        <SignedInContent />
      </SignedIn>
    </>
  );
}

export default App;
