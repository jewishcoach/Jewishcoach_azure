import { Heart, Menu } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { MACRO_STAGES } from './types';
import { useStageFlow } from './hooks/useStageFlow';
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
  const { isSignedIn, isLoaded } = useAuth();

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
  const {
    flowState,
    messages,
    isLoading,
    sendMessage,
    startOnboarding,
    requestNextStageIntro,
    submitIntroAnswers,
  } = useStageFlow(language);

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
      <header className="h-[64px] sm:h-[80px] flex items-center justify-between px-6 sm:px-9 bg-[#2d4658] flex-shrink-0">
        {/* START side (visually RIGHT in RTL): hamburger + avatar + name */}
        <div className="flex items-center gap-4">
          <button type="button" className="p-2 rounded-lg hover:bg-white/10 transition-colors">
            <Menu size={24} className="text-gray-300" />
          </button>
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-white/10 transition-colors cursor-pointer">
            <div className="w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center overflow-hidden">
              <span className="text-white text-xs font-bold">
                {isHe ? 'א' : 'E'}
              </span>
            </div>
            <span className="text-base font-medium text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>
              {isHe ? 'אלי' : 'Eli'}
            </span>
          </div>
        </div>

        {/* END side (visually LEFT in RTL): branding text + icon */}
        <div className="flex items-center gap-3">
          <span className="text-sm sm:text-base font-medium text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>
            {isHe ? 'בני כאן בשבילך, בכל שלב במסע' : 'Benny is here for you, every step of the way'}
          </span>
          <div className="w-10 h-10 rounded bg-[rgba(151,71,255,0.33)] flex items-center justify-center">
            <Heart size={20} className="text-[#03ffe6]" />
          </div>
        </div>
      </header>

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
            language={language}
          />
        )}
      </div>
    </div>
  );
}
