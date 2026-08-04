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
      <div className="h-screen flex items-center justify-center bg-[#faf8f3]">
        <div className="h-9 w-9 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
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
    <div className="h-screen flex flex-col bg-[#faf8f3]" dir={isHe ? 'rtl' : 'ltr'}>
      {/* Header — dark background like Figma */}
      <header className="h-14 sm:h-16 flex items-center justify-between px-4 sm:px-6 bg-slate-800 flex-shrink-0">
        {/* START side (visually RIGHT in RTL): hamburger + avatar + name */}
        <div className="flex items-center gap-3">
          <button type="button" className="p-1.5 rounded-lg hover:bg-slate-700 transition-colors">
            <Menu size={20} className="text-gray-300" />
          </button>
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-teal-600 flex items-center justify-center overflow-hidden">
            <span className="text-white text-xs sm:text-sm font-bold">
              {isHe ? 'א' : 'E'}
            </span>
          </div>
          <span className="text-sm font-medium text-white">
            {isHe ? 'אלי' : 'Eli'}
          </span>
        </div>

        {/* END side (visually LEFT in RTL): branding text + heart */}
        <div className="flex items-center gap-2">
          <span className="text-xs sm:text-sm font-medium text-teal-300">
            {isHe ? 'בני כאן בשבילך, בכל שלב במסע' : 'Benny is here for you, every step of the way'}
          </span>
          <Heart size={18} className="text-teal-400 fill-teal-400" />
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
                <div className="animate-spin w-8 h-8 border-3 border-teal-400 border-t-transparent rounded-full mx-auto" />
                <p className="text-sm text-gray-500">
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
              <div className="animate-spin w-8 h-8 border-3 border-teal-400 border-t-transparent rounded-full" />
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
