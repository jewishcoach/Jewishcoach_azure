import { useState, useEffect, useCallback } from 'react';
import { Heart, Menu, X, LogOut, MessageSquare, User, PlusCircle, Pause } from 'lucide-react';
import { useV3Auth, useV3User } from './hooks/useV3Auth';
import { MACRO_STAGES } from './types';
import { useStageFlowV3 } from './hooks/useStageFlowV3';
import { listConversations, fetchUserGender } from './services/api';
import type { ConversationListItem } from './services/api';

// Reuse V2 components that don't change
import { JourneySidebar } from '../v2/components/JourneySidebar';
import { PauseModal } from '../v2/components/PauseModal';
import { StageCompleteScreen } from '../v2/screens/StageCompleteScreen';
import { StageIntroScreen } from '../v2/screens/StageIntroScreen';
import { WelcomeBackScreen } from '../v2/screens/WelcomeBackScreen';
import { LoginScreen } from '../v2/screens/LoginScreen';
import { QuotaExceededModal } from '../components/QuotaExceededModal';

// V3-specific screens
import { ChatScreen } from './screens/ChatScreen';
import { OnboardingScreen } from './screens/OnboardingScreen';
import { AccountModal } from './components/AccountModal';

// Couple process (shared event, each partner in a private conversation, two shared screens)
import './couple/pendingInvite';
import { useCouple } from './couple/useCouple';
import { CoupleLayer } from './couple/CoupleLayer';
import { UnstartedBanner } from './couple/UnstartedBanner';
import type { Gender } from './couple/coupleApi';
import { gFor } from './couple/lines';

interface V3AppProps {
  language?: string;
}

export function V3App({ language = 'he' }: V3AppProps) {
  const { isSignedIn, isLoaded, signOut, getToken } = useV3Auth();
  const { user } = useV3User();
  const [menuOpen, setMenuOpen] = useState(false);
  const [journeyOpen, setJourneyOpen] = useState(false);
  const [showPauseModal, setShowPauseModal] = useState(false);
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [userGender, setUserGender] = useState<string | null>(null);
  const [accountOpen, setAccountOpen] = useState(false);

  useEffect(() => {
    if (isSignedIn) {
      fetchUserGender(getToken).then(setUserGender);
    }
  }, [isSignedIn, getToken]);

  const loadConversationsList = useCallback(async () => {
    setLoadingConversations(true);
    try {
      const list = await listConversations(getToken);
      setConversations(list);
    } catch (err) {
      console.error('[V3 Menu] loadConversations failed:', err);
    } finally {
      setLoadingConversations(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (menuOpen) loadConversationsList();
  }, [menuOpen, loadConversationsList]);

  const {
    flowState,
    messages,
    conversationId,
    isLoading,
    collectedData,
    sendMessage,
    showStageSummary,
    startOnboarding,
    startNewConversation,
    resumeConversation,
    requestNextStageIntro,
    submitIntroAnswers,
    quotaExceeded,
    dismissQuotaExceeded,
    startConversationWith,
    goToStage,
    savePersonalStatement,
    // V3-specific
    activeTool,
    toolSubmitting,
    submitTool,
    dismissTool,
  } = useStageFlowV3(language);

  const couple = useCouple({ getToken, isSignedIn, startConversationWith, goToStage, resumeConversation });
  const { syncConversation, refreshSessions, clearStatus } = couple;
  useEffect(() => {
    if (menuOpen) refreshSessions();  // the ♥ marks in the conversation list
  }, [menuOpen, refreshSessions]);
  const currentStep = flowState.currentStep;
  // The open conversation changed (start / resume / reload): find its couple process and, at a couple step, show it
  useEffect(() => {
    if (conversationId) syncConversation(conversationId, currentStep);
    else clearStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when the conversation changes, with its step at that moment
  }, [conversationId, syncConversation, clearStatus]);
  const coupleActive = !!couple.status && couple.status.status !== 'cancelled' && !couple.status.me.left;

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (flowState.phase === 'chatting' && messages.length > 0) {
        e.preventDefault();
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [flowState.phase, messages.length]);

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

  if (flowState.phase === 'initializing') {
    return (
      <div className="h-screen flex items-center justify-center bg-[#f6f4f0]">
        <div className="h-9 w-9 animate-spin rounded-full border-2 border-[#03ffe6] border-t-transparent" />
      </div>
    );
  }

  const isHe = language.startsWith('he');
  const currentMacroIdx = MACRO_STAGES.findIndex((s) => s.id === flowState.currentMacroStage);
  const currentMacro = currentMacroIdx >= 0 ? MACRO_STAGES[currentMacroIdx] : undefined;
  const stageTitle = currentMacro ? (isHe ? currentMacro.title_he : currentMacro.title_en) : '';
  const stageNumber = currentMacroIdx + 1;

  const handleOnboardingComplete = (emotions: string[], domain: string, freeText?: string) => {
    startOnboarding(emotions, domain, freeText);
  };

  return (
    <div className="h-screen flex flex-col bg-[#f6f4f0]" dir={isHe ? 'rtl' : 'ltr'}>
      {/* Header */}
      <header className="h-[64px] lg:h-[80px] flex items-center justify-between px-4 lg:px-9 bg-[#2d4658] flex-shrink-0" dir="ltr">
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => setMenuOpen(true)} className="p-2 rounded-lg hover:bg-white/10 transition-colors">
            <Menu size={24} className="text-gray-300" />
          </button>
          {flowState.phase === 'chatting' && (
            <button type="button" onClick={() => setShowPauseModal(true)} className="p-2 rounded-lg hover:bg-white/10 transition-colors" title={isHe ? 'שמור ועצור' : 'Save & pause'}>
              <Pause size={18} className="text-gray-300" />
            </button>
          )}
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

        <div className="flex items-center gap-3">
          {/* V3 badge */}
          <span className="hidden lg:inline px-2 py-0.5 rounded text-[10px] font-bold bg-[#9747ff] text-white">V3</span>
          <span className="hidden lg:inline text-sm sm:text-base font-medium text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>
            {isHe ? 'בני כאן בשבילך, בכל שלב במסע' : 'Benny is here for you, every step of the way'}
          </span>
          <button type="button" onClick={() => setJourneyOpen(true)} className="w-10 h-10 rounded bg-[rgba(151,71,255,0.33)] flex items-center justify-center lg:pointer-events-none">
            <Heart size={20} className="text-[#03ffe6]" />
          </button>
        </div>
      </header>

      {/* Side menu drawer — identical to V2 */}
      {menuOpen && (
        <>
          <div className="fixed inset-0 bg-black/40 z-40" onClick={() => setMenuOpen(false)} />
          <div className="fixed top-0 left-0 h-full w-[300px] bg-[#2d4658] z-50 shadow-xl flex flex-col animate-[slideIn_0.2s_ease-out]" dir="rtl">
            <div className="flex items-center justify-between p-5 border-b border-[rgba(3,255,230,0.2)]">
              <h2 className="text-lg font-semibold text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>תפריט</h2>
              <button type="button" onClick={() => setMenuOpen(false)} className="p-1 rounded-lg hover:bg-white/10">
                <X size={20} className="text-gray-300" />
              </button>
            </div>
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
            <div className="p-3">
              <button
                type="button"
                onClick={() => { startNewConversation(); setMenuOpen(false); }}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-[#9747ff] hover:bg-[#8035e6] transition-colors text-right"
              >
                <PlusCircle size={18} className="text-white flex-shrink-0" />
                <span className="text-sm font-semibold text-white" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  {isHe ? 'שיחה חדשה' : 'New conversation'}
                </span>
              </button>
              {couple.canStart && (
                <button
                  type="button"
                  onClick={() => { couple.openStart(); setMenuOpen(false); }}
                  className="w-full mt-2 flex items-center gap-3 px-4 py-3 rounded-xl border border-[#9747ff] hover:bg-white/10 transition-colors text-right"
                >
                  <Heart size={18} className="text-[#03ffe6] flex-shrink-0" />
                  <span className="text-sm font-semibold text-white" style={{ fontFamily: "'Heebo', sans-serif" }}>
                    תהליך זוגי חדש
                  </span>
                </button>
              )}
            </div>
            <div className="px-3">
              <button
                type="button"
                onClick={() => { setAccountOpen(true); setMenuOpen(false); }}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/10 transition-colors text-right"
              >
                <User size={18} className="text-[#03ffe6] flex-shrink-0" />
                <span className="text-sm text-white" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  {isHe ? 'החשבון שלי' : 'My account'}
                </span>
              </button>
            </div>
            {flowState.phase === 'chatting' && (
              <div className="px-3">
                <button
                  type="button"
                  onClick={() => { setShowPauseModal(true); setMenuOpen(false); }}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/10 transition-colors text-right"
                >
                  <Pause size={18} className="text-[#03ffe6] flex-shrink-0" />
                  <span className="text-sm text-white" style={{ fontFamily: "'Heebo', sans-serif" }}>
                    {isHe ? 'שמור ועצור' : 'Save & pause'}
                  </span>
                </button>
              </div>
            )}
            <div className="flex-1 overflow-y-auto p-3 space-y-1 scrollbar-hide" style={{ scrollbarWidth: 'none' }}>
              <p className="px-4 py-2 text-xs font-semibold text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                {isHe ? 'השיחות שלי' : 'My conversations'}
              </p>
              {loadingConversations && (
                <div className="flex justify-center py-4">
                  <div className="animate-spin w-5 h-5 border-2 border-[#03ffe6] border-t-transparent rounded-full" />
                </div>
              )}
              {!loadingConversations && conversations.length === 0 && (
                <p className="px-4 py-2 text-xs text-[rgba(255,255,255,0.4)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  {isHe ? 'אין שיחות קודמות' : 'No conversations yet'}
                </p>
              )}
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  type="button"
                  onClick={() => { couple.close(); resumeConversation(conv.id); setMenuOpen(false); }}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/10 transition-colors text-right"
                >
                  {couple.sessions.some((s) => s.conversation_id === conv.id)
                    ? <Heart size={16} className="text-[#03ffe6] flex-shrink-0" />
                    : <MessageSquare size={16} className="text-[#03ffe6] flex-shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white truncate" style={{ fontFamily: "'Heebo', sans-serif" }}>
                      {isHe && /^New Conversation/.test(conv.title || '') ? 'שיחת אימון' : conv.title}
                    </p>
                    <p className="text-xs text-[rgba(255,255,255,0.4)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                      {new Date(conv.created_at).toLocaleDateString('he-IL')} · {conv.message_count} הודעות
                    </p>
                  </div>
                </button>
              ))}
            </div>
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

      {/* Journey drawer (mobile) */}
      {journeyOpen && flowState.phase !== 'onboarding' && flowState.phase !== 'welcome_back' && (
        <>
          <div className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={() => setJourneyOpen(false)} />
          <div className="fixed top-0 right-0 h-full w-[330px] z-50 lg:hidden animate-[slideIn_0.2s_ease-out] [&_aside]:flex [&_aside]:flex-col [&_aside]:h-full [&_aside]:overflow-y-auto" dir="rtl">
            <button type="button" onClick={() => setJourneyOpen(false)} className="absolute top-4 left-4 p-1 rounded-lg hover:bg-white/10 z-10">
              <X size={20} className="text-gray-300" />
            </button>
            <JourneySidebar
              currentMacroStage={flowState.currentMacroStage}
              currentStep={flowState.currentStep}
              collectedData={collectedData}
              language={language}
              inDrawer
            />
          </div>
        </>
      )}

      {/* Modals */}
      <AccountModal
        open={accountOpen}
        onClose={() => setAccountOpen(false)}
        getToken={getToken}
        onSaved={(p) => setUserGender(p.gender)}
      />
      <PauseModal
        isOpen={showPauseModal}
        stageNumber={stageNumber}
        onContinue={() => setShowPauseModal(false)}
        onGoHome={() => { setShowPauseModal(false); startNewConversation(); }}
        gender={userGender}
      />
      <QuotaExceededModal
        isOpen={quotaExceeded}
        onClose={dismissQuotaExceeded}
        onGoToSubscription={() => { window.location.href = '/billing'; }}
      />

      {/* Main content */}
      <div className="flex-1 flex min-h-0">
        <main className="flex-1 flex flex-col min-h-0">
          {couple.view && (
            <CoupleLayer couple={couple} defaultName={user?.firstName || ''} profileGender={(userGender as Gender | null) ?? null} />
          )}

          {!couple.view && <>
          {flowState.phase === 'welcome_back' && conversationId && (
            <div className="flex-1 flex flex-col min-h-0 animate-[fadeIn_0.3s_ease-out]">
              <WelcomeBackScreen
                stageTitle={stageTitle}
                stageNumber={stageNumber}
                personalStatement={undefined}
                lastActiveDate={undefined}
                onContinue={() => resumeConversation(conversationId)}
                onGoHome={startNewConversation}
              />
            </div>
          )}

          {flowState.phase === 'onboarding' && (
            <div className="flex-1 flex flex-col min-h-0 animate-[fadeIn_0.3s_ease-out]">
              {couple.ongoing && couple.ongoing.conversation_id && (
                <UnstartedBanner
                  session={couple.ongoing}
                  onStart={() => {
                    const s = couple.ongoing!;
                    if (!s.me.step || s.me.step === 'S0') couple.beginMyPart(s.conversation_id as number, s.session_id, s.event_title);
                    else resumeConversation(s.conversation_id as number);
                  }}
                />
              )}
              <OnboardingScreen
                onComplete={handleOnboardingComplete}
                gender={userGender}
                onStartCouple={couple.canStart ? couple.openStart : undefined}
              />
            </div>
          )}

          {flowState.phase === 'chatting' && (
            <div className="flex-1 flex flex-col min-h-0 animate-[fadeIn_0.3s_ease-out]">
              <ChatScreen
                messages={messages}
                onSend={sendMessage}
                isLoading={isLoading}
                stageTitle={stageTitle}
                stageNumber={stageNumber}
                currentStep={flowState.currentStep}
                activeTool={activeTool}
                toolSubmitting={toolSubmitting}
                onSubmitTool={submitTool}
                onDismissTool={dismissTool}
                onShowSummary={flowState.pendingSummary ? showStageSummary : undefined}
              />
            </div>
          )}

          {flowState.phase === 'stage_complete' && flowState.summary && (
            <div className="flex-1 flex flex-col min-h-0 animate-[fadeIn_0.3s_ease-out]">
              <StageCompleteScreen
                summary={flowState.summary}
                onContinue={coupleActive && couple.status && flowState.summary.stage_id === 'discovery'
                  ? async (statement) => {
                    // couple process: after discovery comes the preview of the shared lines, not כמ"ז
                    await savePersonalStatement(statement);
                    if (!(await couple.openCheckpoint('mirror', couple.status!.session_id))) requestNextStageIntro();
                  }
                  : requestNextStageIntro}
                continueLabel={coupleActive && flowState.summary.stage_id === 'discovery' ? 'להמשך: מה לשתף' : undefined}
                nextStepText={coupleActive && flowState.summary.stage_id === 'discovery'
                  ? (couple.status?.partner
                    ? `הצעד הבא — לבחור מה ${couple.status.partner.name} ${gFor(couple.status.partner.gender)('יראה', 'תראה')} מהשלב הזה`
                    : 'הצעד הבא — לבחור מה בן/בת הזוג יראו מהשלב הזה')
                  : undefined}
                extraAction={coupleActive && couple.status && !flowState.summary.next_stage_id
                  ? { label: 'למסך ההתחייבות הזוגית', onClick: () => { couple.openCheckpoint('commitment', couple.status!.session_id); } }
                  : undefined}
                language={language}
                conversationId={conversationId}
                userMessages={messages.filter((m) => m.role === 'user').map((m) => m.content)}
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
                previousInsights={flowState.summary?.insights}
                userGender={userGender}
              />
            </div>
          )}

          {flowState.phase === 'submitting_answers' && (
            <div className="flex-1 flex items-center justify-center animate-[fadeIn_0.3s_ease-out]">
              <div className="animate-spin w-8 h-8 border-3 border-[#03ffe6] border-t-transparent rounded-full" />
            </div>
          )}
          </>}
        </main>

        {flowState.phase !== 'onboarding' && flowState.phase !== 'welcome_back' && (
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
