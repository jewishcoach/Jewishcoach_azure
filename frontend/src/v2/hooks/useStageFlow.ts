import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import type {
  ChatMessage,
  ChatResponseV2,
  CollectedData,
  FlowState,
  StageIntroPayload,
  StageSummaryPayload,
} from '../types';
import { stepToMacroStage } from '../types';
import {
  createConversation,
  fetchStageIntro,
  listConversations,
  loadConversation,
  sendMessageV2,
  submitStageIntroAnswers,
} from '../services/api';
import { getApiBase } from '../../config';

const INITIAL_FLOW_STATE: FlowState = {
  phase: 'initializing',
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
  const [collectedData, setCollectedData] = useState<CollectedData>({});

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
        if (response.collected_data) {
          setCollectedData((prev) => ({ ...prev, ...response.collected_data }));
        }

        setFlowState((prev) => ({
          ...prev,
          currentStep: response.current_step,
          currentMacroStage: stepToMacroStage(response.current_step || prev.currentStep || 'S0'),
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

  const startOnboarding = useCallback(async (emotions?: string[], domain?: string) => {
    setFlowState((prev) => ({
      ...prev,
      phase: 'chatting',
      currentMacroStage: 'identification',
    }));
    setIsLoading(true);

    try {
      const contextMessage = [
        emotions?.length ? `אני מרגיש: ${emotions.join(', ')}` : '',
        domain ? `בתחום: ${domain}` : '',
      ].filter(Boolean).join('. ');

      const convId = await createConversation(language, getToken);
      setConversationId(convId);

      const response = await sendMessageV2(
        contextMessage || 'אני רוצה להתחיל',
        convId,
        language,
        getToken,
      );

      const assistantMsg: ChatMessage = {
        id: `a-opening-${Date.now()}`,
        role: 'assistant',
        content: response.coach_message,
        phase: response.current_step,
        suggestions: response.suggestions,
      };
      setMessages([assistantMsg]);

      if (response.collected_data) {
        setCollectedData((prev) => ({ ...prev, ...response.collected_data }));
      }
    } catch (err) {
      console.error('[V2 Chat] startOnboarding error:', err, 'context:', { emotions, domain });
      const fallbackMsg: ChatMessage = {
        id: `a-opening-${Date.now()}`,
        role: 'assistant',
        content: 'ספר לי קצת על מה שעובר עליך בתקופה הזו?',
        phase: 'S1',
      };
      setMessages([fallbackMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [language, getToken]);

  const requestNextStageIntro = useCallback(async (personalStatement?: string) => {
    if (!conversationId || !flowState.summary?.next_stage_id) return;
    const nextStageId = flowState.summary.next_stage_id;

    if (personalStatement) {
      try {
        const base = getApiBase();
        await fetch(`${base}/chat/v2/conversations/${conversationId}/statement`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...(await getToken() ? { Authorization: `Bearer ${await getToken()}` } : {}) },
          body: JSON.stringify({ stage_id: flowState.currentMacroStage, statement: personalStatement }),
        });
      } catch { /* best effort */ }
    }

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
        setMessages([]);
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

  const resumeConversation = useCallback(async (convId: number) => {
    setIsLoading(true);
    try {
      const data = await loadConversation(convId, getToken);
      setConversationId(data.conversation_id);
      setMessages(data.messages as ChatMessage[]);
      if (data.collected_data) {
        setCollectedData(data.collected_data as CollectedData);
      }
      setFlowState((prev) => ({
        ...prev,
        phase: 'chatting',
        currentStep: data.current_step,
        currentMacroStage: stepToMacroStage(data.current_step || 'S0'),
      }));
    } catch (err) {
      console.error('[V2 Chat] resumeConversation error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [getToken]);

  const startNewConversation = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setCollectedData({});
    setSaturationScore(0);
    setFlowState({
      phase: 'onboarding',
      currentMacroStage: 'identification',
      currentStep: 'S0',
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const convs = await listConversations(getToken);
        if (cancelled) return;
        const recent = convs.find((c) => c.current_phase && c.current_phase !== 'S0' && c.message_count > 2);
        if (recent) {
          setConversationId(recent.id);
          setFlowState({
            phase: 'welcome_back',
            currentMacroStage: stepToMacroStage(recent.current_phase),
            currentStep: recent.current_phase,
          });
        } else {
          setFlowState((prev) => ({ ...prev, phase: 'onboarding' }));
        }
      } catch {
        if (!cancelled) setFlowState((prev) => ({ ...prev, phase: 'onboarding' }));
      }
    })();
    return () => { cancelled = true; };
  }, [getToken]);

  return {
    flowState,
    messages,
    conversationId,
    isLoading,
    saturationScore,
    collectedData,
    sendMessage,
    startOnboarding,
    startNewConversation,
    resumeConversation,
    requestNextStageIntro,
    submitIntroAnswers,
  };
}
