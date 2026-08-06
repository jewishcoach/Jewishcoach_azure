import { useState, useEffect, useCallback } from 'react';
import { Heart, Menu, X, LogOut, MessageSquare, User } from 'lucide-react';
import { useAuth, useUser } from '@clerk/clerk-react';
import { MACRO_STAGES } from './types';
import { useStageFlow } from './hooks/useStageFlow';
import { listConversations, type ConversationListItem } from './services/api';
import { JourneySidebar } from './components/JourneySidebar';
import { ChatScreen } from './screens/ChatScreen';
import { StageCompleteScreen } from './screens/StageCompleteScreen';
import { StageIntroScreen } from './screens/StageIntroScreen';
import { OnboardingScreen } from './screens/OnboardingScreen';
import { LoginScreen } from './screens/LoginScreen';

interface V2AppProps {
  language?: string;
}

export function V2App({ language = 'he' }: V2AppProps) {
  const { isSignedIn, isLoaded, signOut, getToken } = useAuth();
  const { user } = useUser();
  const [menuOpen, setMenuOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);

  const loadConversations = useCallback(async () => {
    const list = await listConversations(getToken);
    setConversations(list);
  }, [getToken]);

  useEffect(() => {
    if (menuOpen) loadConversations();
  }, [menuOpen, loadConversations]);
  const {
    flowState,
    messages,
    isLoading,
    collectedData,
    sendMessage,
    startOnboarding,
    requestNextStageIntro,
    submitIntroAnswers,
  } = useStageFlow(language);

  if (!isLoaded) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#f6f4f0]">
        <div className="h-9 w-9 animate-spin rounded-full border-2 border-[#03ffe6] border-t-transparent" />
      </div>
    );
  }

  if (!isSignedIn) {
    return <LoginScreen />;
  }

  const isHe = language.startsWith('he');
  const currentMacro = MACRO_STAGES.find((s) => s.id === flowState.currentMacroStage);
  const stageTitle = currentMacro
    ? isHe
      ? currentMacro.title_he
      : currentMacro.title_en
    : '';

  const handleOnboardingComplete = (emotions: string[], domain: string) => {
    startOnboarding(emotions, domain);
  };

  return (
    <div className="h-screen flex flex-col bg-[#f6f4f0]" dir={isHe ? 'rtl' : 'ltr'}>
      {/* Header */}
      <header className="h-[64px] lg:h-[80px] flex items-center justify-between px-4 lg:px-9 bg-[#2d4658] flex-shrink-0" dir="ltr">
        {/* Left side: hamburger + avatar + name */}
        <div className="flex items-center gap-4">
          <button type="button" onClick={() => setMenuOpen(true)} className="p-2 rounded-lg hover:bg-white/10 transition-colors">
            <Menu size={24} className="text-gray-300" />
          </button>
          <div className="flex items-center gap-2 px-2 lg:px-4 py-2 rounded-lg hover:bg-white/10 transition-colors cursor-pointer">
            <div className="w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center overflow-hidden">
              <span className="text-white text-xs font-bold">
                {user?.firstName?.charAt(0) || (isHe ? 'א' : 'E')}
              </span>
            </div>
            <span className="hidden lg:inline text-base font-medium text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>
              {user?.firstName || (isHe ? 'אלי' : 'Eli')}
            </span>
          </div>
        </div>

        {/* Right side: branding text (hidden on mobile) + icon */}
        <div className="flex items-center gap-3">
          <span className="hidden lg:inline text-sm sm:text-base font-medium text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>
            {isHe ? 'בני כאן בשבילך, בכל שלב במסע' : 'Benny is here for you, every step of the way'}
          </span>
          <div className="w-10 h-10 rounded bg-[rgba(151,71,255,0.33)] flex items-center justify-center">
            <Heart size={20} className="text-[#03ffe6]" />
          </div>
        </div>
      </header>

      {/* Side menu drawer */}
      {menuOpen && (
        <>
          <div className="fixed inset-0 bg-black/40 z-40" onClick={() => setMenuOpen(false)} />
          <div className="fixed top-0 left-0 h-full w-[300px] bg-[#2d4658] z-50 shadow-xl flex flex-col animate-[slideIn_0.2s_ease-out]" dir="rtl">
            {/* Close button */}
            <div className="flex items-center justify-between p-5 border-b border-[rgba(3,255,230,0.2)]">
              <h2 className="text-lg font-semibold text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>תפריט</h2>
              <button type="button" onClick={() => setMenuOpen(false)} className="p-1 rounded-lg hover:bg-white/10">
                <X size={20} className="text-gray-300" />
              </button>
            </div>

            {/* Profile */}
            <div className="p-5 border-b border-[rgba(3,255,230,0.2)]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-teal-600 flex items-center justify-center">
                  <User size={18} className="text-white" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white" style={{ fontFamily: "'Heebo', sans-serif" }}>
                    {user?.firstName || ''} {user?.lastName || ''}
                  </p>
                  <p className="text-xs text-[rgba(255,255,255,0.5)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                    {user?.primaryEmailAddress?.emailAddress || ''}
                  </p>
                </div>
              </div>
            </div>

            {/* Conversations list */}
            <div className="flex-1 overflow-y-auto p-3 space-y-1">
              <p className="px-4 py-2 text-xs font-semibold text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                {isHe ? 'השיחות שלי' : 'My conversations'}
              </p>
              {conversations.length === 0 && (
                <p className="px-4 py-2 text-xs text-[rgba(255,255,255,0.4)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  {isHe ? 'אין שיחות קודמות' : 'No conversations yet'}
                </p>
              )}
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  type="button"
                  onClick={() => setMenuOpen(false)}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/10 transition-colors text-right"
                >
                  <MessageSquare size={16} className="text-[#03ffe6] flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white truncate" style={{ fontFamily: "'Heebo', sans-serif" }}>
                      {conv.title}
                    </p>
                    <p className="text-xs text-[rgba(255,255,255,0.4)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                      {new Date(conv.created_at).toLocaleDateString('he-IL')} · {conv.message_count} הודעות
                    </p>
                  </div>
                </button>
              ))}
            </div>

            {/* Logout */}
            <div className="p-5 border-t border-[rgba(3,255,230,0.2)]">
              <button
                type="button"
                onClick={() => signOut()}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/10 transition-colors"
              >
                <LogOut size={18} className="text-red-400" />
                <span className="text-sm text-red-400" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  {isHe ? 'התנתקות' : 'Sign out'}
                </span>
              </button>
            </div>
          </div>
        </>
      )}

      {/* Main content area */}
      <div className="flex-1 flex min-h-0">
        {/* Chat / Screens area */}
        <main className="flex-1 flex flex-col min-h-0">
          {flowState.phase === 'onboarding' && (
            <div className="flex-1 flex flex-col min-h-0 animate-[fadeIn_0.3s_ease-out]">
              <OnboardingScreen onComplete={handleOnboardingComplete} />
            </div>
          )}

          {flowState.phase === 'chatting' && (
            <div className="flex-1 flex flex-col min-h-0 animate-[fadeIn_0.3s_ease-out]">
              <ChatScreen
                messages={messages}
                onSend={sendMessage}
                isLoading={isLoading}
                stageTitle={stageTitle}
              />
            </div>
          )}

          {flowState.phase === 'stage_complete' && flowState.summary && (
            <div className="flex-1 flex flex-col min-h-0 animate-[fadeIn_0.3s_ease-out]">
              <StageCompleteScreen
                summary={flowState.summary}
                onContinue={requestNextStageIntro}
                language={language}
              />
            </div>
          )}

          {flowState.phase === 'loading_intro' && (
            <div className="flex-1 flex items-center justify-center animate-[fadeIn_0.3s_ease-out]">
              <div className="text-center space-y-3">
                <div className="animate-spin w-8 h-8 border-3 border-[#03ffe6] border-t-transparent rounded-full mx-auto" />
                <p className="text-sm text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  {isHe ? 'מכין את השלב הבא...' : 'Preparing next stage...'}
                </p>
              </div>
            </div>
          )}

          {flowState.phase === 'answering_intro' && flowState.introPayload && (
            <div className="flex-1 flex flex-col min-h-0 animate-[fadeIn_0.3s_ease-out]">
              <StageIntroScreen
                payload={flowState.introPayload}
                onSubmit={submitIntroAnswers}
                isSubmitting={false}
              />
            </div>
          )}

          {flowState.phase === 'submitting_answers' && (
            <div className="flex-1 flex items-center justify-center animate-[fadeIn_0.3s_ease-out]">
              <div className="animate-spin w-8 h-8 border-3 border-[#03ffe6] border-t-transparent rounded-full" />
            </div>
          )}
        </main>

        {/* Journey Sidebar — hidden during onboarding */}
        {flowState.phase !== 'onboarding' && (
          <JourneySidebar
            currentMacroStage={flowState.currentMacroStage}
            currentStep={flowState.currentStep}
            collectedData={collectedData}
            language={language}
          />
        )}
      </div>
    </div>
  );
}
