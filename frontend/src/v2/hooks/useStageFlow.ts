import { useCallback, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import type {
  ChatMessage,
  ChatResponseV2,
  FlowState,
  StageIntroPayload,
  StageSummaryPayload,
} from '../types';
import {
  createConversation,
  fetchStageIntro,
  sendMessageV2,
  submitStageIntroAnswers,
} from '../services/api';

const INITIAL_FLOW_STATE: FlowState = {
  phase: 'onboarding',
  currentMacroStage: 'identification',
  currentStep: 'S0',
};

export function useStageFlow(language: string = 'he') {
  const { getToken } = useAuth();
  const [flowState, setFlowState] = useState<FlowState>(INITIAL_FLOW_STATE);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [saturationScore, setSaturationScore] = useState(0);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim()) return;
      setIsLoading(true);

      try {
        let convId = conversationId;
        if (!convId) {
          convId = await createConversation(language, getToken);
          setConversationId(convId);
        }

        const userMsg: ChatMessage = {
          id: `u-${Date.now()}`,
          role: 'user',
          content: text,
        };
        setMessages((prev) => [...prev, userMsg]);

        const response: ChatResponseV2 = await sendMessageV2(
          text,
          convId,
          language,
          getToken,
        );

        const assistantMsg: ChatMessage = {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: response.coach_message,
          phase: response.current_step,
          suggestions: response.suggestions,
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setSaturationScore(response.saturation_score);

        setFlowState((prev) => ({
          ...prev,
          currentStep: response.current_step,
        }));

        if (response.stage_complete) {
          setFlowState((prev) => ({
            ...prev,
            phase: 'stage_complete',
            summary: response.stage_complete as StageSummaryPayload,
          }));
        }
      } catch (err) {
        console.error('[V2 Chat] sendMessage error:', err);
        const errorMsg: ChatMessage = {
          id: `e-${Date.now()}`,
          role: 'assistant',
          content: 'סליחה, משהו השתבש. נסה שוב בבקשה.',
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [conversationId, language, getToken],
  );

  const startOnboarding = useCallback((emotions?: string[], domain?: string) => {
    const openingQuestion = domain
      ? `איך ה${domain === 'עבודה' ? 'תקיעות בעבודה' : domain === 'זוגיות' ? 'קושי בזוגיות' : domain === 'משפחה' ? 'מתח במשפחה' : 'מה שמטריד אותך'} בא לידי ביטוי ביום-יום שלך?`
      : 'ספר לי קצת על מה שעובר עליך בתקופה הזו?';

    const openingSuggestions = domain
      ? ['עבודה', 'משפחה וקשרים', 'בריאות ורווחה', 'אחר']
      : ['עבודה', 'זוגיות', 'משפחה', 'אחר'];

    const openingMsg: ChatMessage = {
      id: `a-opening-${Date.now()}`,
      role: 'assistant',
      content: openingQuestion,
      phase: 'S1',
      suggestions: openingSuggestions,
    };
    setMessages([openingMsg]);

    setFlowState((prev) => ({
      ...prev,
      phase: 'chatting',
      currentMacroStage: 'identification',
    }));
  }, []);

  const requestNextStageIntro = useCallback(async () => {
    if (!conversationId || !flowState.summary?.next_stage_id) return;
    const nextStageId = flowState.summary.next_stage_id;

    setFlowState((prev) => ({
      ...prev,
      phase: 'loading_intro',
      currentMacroStage: nextStageId,
    }));

    try {
      const intro: StageIntroPayload = await fetchStageIntro(
        conversationId,
        nextStageId,
        language,
        getToken,
      );
      setFlowState((prev) => ({
        ...prev,
        phase: 'answering_intro',
        introPayload: intro,
      }));
    } catch {
      setFlowState((prev) => ({ ...prev, phase: 'chatting' }));
    }
  }, [conversationId, flowState.summary, language, getToken]);

  const submitIntroAnswers = useCallback(
    async (answers: Record<string, string[]>) => {
      if (!conversationId) return;
      const macroStage = flowState.currentMacroStage;

      setFlowState((prev) => ({ ...prev, phase: 'submitting_answers' }));

      try {
        await submitStageIntroAnswers(
          conversationId,
          macroStage,
          answers,
          language,
          getToken,
        );
        setFlowState((prev) => ({
          ...prev,
          phase: 'chatting',
          introPayload: undefined,
          summary: undefined,
        }));
      } catch {
        setFlowState((prev) => ({ ...prev, phase: 'answering_intro' }));
      }
    },
    [conversationId, flowState.currentMacroStage, language, getToken],
  );

  return {
    flowState,
    messages,
    conversationId,
    isLoading,
    saturationScore,
    sendMessage,
    startOnboarding,
    requestNextStageIntro,
    submitIntroAnswers,
  };
}
