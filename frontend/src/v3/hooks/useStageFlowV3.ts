import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import type {
  ChatResponseV2,
  CollectedData,
  FlowState,
  StageIntroPayload,
  StageSummaryPayload,
  ActiveInlineTool,
  ToolCallV3,
  V3ChatMessage,
} from '../types';
import { stepToMacroStage } from '../types';
import {
  createConversation,
  fetchStageIntro,
  listConversations,
  loadConversation,
  sendMessageV3,
  submitStageIntroAnswers,
  submitToolResponse,
  QuotaExceededError,
  ConflictError,
} from '../services/api';
import { getApiBase } from '../../config';

const INITIAL_FLOW_STATE: FlowState = {
  phase: 'initializing',
  currentMacroStage: 'identification',
  currentStep: 'S0',
};

const SESSION_KEY = 'v3_session_state';

interface PersistedSession {
  conversationId: number;
  flowState: FlowState;
  messages: V3ChatMessage[];
  collectedData: CollectedData;
  saturationScore: number;
}

function saveSession(data: PersistedSession) {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(data));
  } catch { /* storage full or unavailable */ }
}

function loadSession(): PersistedSession | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as PersistedSession;
  } catch {
    return null;
  }
}

function clearSession() {
  try { sessionStorage.removeItem(SESSION_KEY); } catch { /* */ }
}

function toolCallToActiveTool(tc: Record<string, unknown>): ActiveInlineTool | null {
  if (!tc || !tc.tool_type) return null;
  return {
    id: (tc.id as string) || `tool-${Date.now()}`,
    tool_type: tc.tool_type as string,
    data: (tc.data as Record<string, unknown>) || undefined,
    title_he: (tc.title_he as string) || undefined,
    instruction_he: (tc.instruction_he as string) || undefined,
  };
}

export function useStageFlowV3(language: string = 'he') {
  const { getToken, isSignedIn } = useAuth();
  const [flowState, setFlowState] = useState<FlowState>(INITIAL_FLOW_STATE);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<V3ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [saturationScore, setSaturationScore] = useState(0);
  const [collectedData, setCollectedData] = useState<CollectedData>({});
  const [quotaExceeded, setQuotaExceeded] = useState(false);

  // V3-specific: inline tool state
  const [activeTool, setActiveTool] = useState<ActiveInlineTool | null>(null);
  const [toolSubmitting, setToolSubmitting] = useState(false);

  // ---------------------------------------------------------------------------
  // Process a chat response — shared by sendMessage and startOnboarding
  // ---------------------------------------------------------------------------
  const processResponse = useCallback((response: ChatResponseV2, convId: number) => {
    const assistantMsg: V3ChatMessage = {
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

    // Check for tool_call → activate inline tool
    if (response.tool_call) {
      const tool = toolCallToActiveTool(response.tool_call);
      if (tool) setActiveTool(tool);
    }

    if (response.stage_complete) {
      setFlowState((prev) => ({
        ...prev,
        phase: 'stage_complete',
        summary: response.stage_complete as StageSummaryPayload,
      }));
    }

    // Persist session
    setMessages((msgs) => {
      setCollectedData((cd) => {
        saveSession({
          conversationId: convId,
          flowState: {
            phase: response.stage_complete ? 'stage_complete' : 'chatting',
            currentMacroStage: stepToMacroStage(response.current_step || 'S0'),
            currentStep: response.current_step,
            ...(response.stage_complete ? { summary: response.stage_complete as StageSummaryPayload } : {}),
          },
          messages: msgs,
          collectedData: response.collected_data ? { ...cd, ...response.collected_data } : cd,
          saturationScore: response.saturation_score,
        });
        return cd;
      });
      return msgs;
    });
  }, []);

  // ---------------------------------------------------------------------------
  // Send chat message
  // ---------------------------------------------------------------------------
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim()) return;
      setIsLoading(true);
      setActiveTool(null);

      try {
        let convId = conversationId;
        if (!convId) {
          convId = await createConversation(language, getToken);
          setConversationId(convId);
        }

        const userMsg: V3ChatMessage = {
          id: `u-${Date.now()}`,
          role: 'user',
          content: text,
        };
        setMessages((prev) => [...prev, userMsg]);

        const response = await sendMessageV3(text, convId, language, getToken);

        // Inline response processing (not via callback — avoids React 18 batching issues)
        const assistantMsg: V3ChatMessage = {
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

        if (response.tool_call) {
          const tool = toolCallToActiveTool(response.tool_call);
          if (tool) setActiveTool(tool);
        }

        if (response.stage_complete) {
          setFlowState((prev) => ({
            ...prev,
            phase: 'stage_complete',
            summary: response.stage_complete as StageSummaryPayload,
          }));
        }
      } catch (err) {
        if (err instanceof QuotaExceededError) {
          setQuotaExceeded(true);
          return;
        }
        if (err instanceof ConflictError) {
          setMessages((prev) => [...prev, {
            id: `e-${Date.now()}`,
            role: 'assistant',
            content: 'ההודעה נשלחה פעמיים — שלח שוב בבקשה.',
          }]);
          return;
        }
        console.error('[V3 Chat] sendMessage error:', err);
        setMessages((prev) => [...prev, {
          id: `e-${Date.now()}`,
          role: 'assistant',
          content: 'סליחה, משהו השתבש. נסה שוב בבקשה.',
        }]);
      } finally {
        setIsLoading(false);
      }
    },
    [conversationId, language, getToken],
  );

  // ---------------------------------------------------------------------------
  // Submit inline tool
  // ---------------------------------------------------------------------------
  const submitTool = useCallback(
    async (toolType: string, data: Record<string, unknown>) => {
      if (!conversationId || toolSubmitting) return;
      setToolSubmitting(true);

      try {
        // Add a completed tool card to messages
        const toolMsg: V3ChatMessage = {
          id: `t-${Date.now()}`,
          role: 'tool_result',
          content: '',
          toolResult: { tool_type: toolType, data },
        };
        setMessages((prev) => [...prev, toolMsg]);
        setActiveTool(null);

        const response = await submitToolResponse(conversationId, toolType, data, getToken);

        if (response.coach_message) {
          const assistantMsg: V3ChatMessage = {
            id: `a-${Date.now()}`,
            role: 'assistant',
            content: response.coach_message,
            phase: response.current_step,
          };
          setMessages((prev) => [...prev, assistantMsg]);
        }
        if (response.saturation_score != null) {
          setSaturationScore(response.saturation_score);
        }

        if (response.collected_data) {
          setCollectedData((prev) => ({ ...prev, ...response.collected_data }));
        }

        if (response.current_step) {
          setFlowState((prev) => ({
            ...prev,
            currentStep: response.current_step,
            currentMacroStage: stepToMacroStage(response.current_step || prev.currentStep || 'S0'),
          }));
        }

        // Check for chained tool_call
        if (response.tool_call) {
          const next = toolCallToActiveTool(response.tool_call as Record<string, unknown>);
          if (next) setActiveTool(next);
        }
      } catch (err) {
        console.error('[V3 Chat] submitTool error:', err);
        setMessages((prev) => [...prev, {
          id: `e-${Date.now()}`,
          role: 'assistant',
          content: 'סליחה, משהו השתבש. נסה שוב בבקשה.',
        }]);
        // Re-show the tool so user can retry
        setActiveTool((prev) => prev);
      } finally {
        setToolSubmitting(false);
      }
    },
    [conversationId, toolSubmitting, getToken],
  );

  // ---------------------------------------------------------------------------
  // Dismiss tool (skip to chat)
  // ---------------------------------------------------------------------------
  const dismissTool = useCallback(() => {
    setActiveTool(null);
  }, []);

  // ---------------------------------------------------------------------------
  // Start onboarding — V3 accepts optional freeText
  // ---------------------------------------------------------------------------
  const startOnboarding = useCallback(async (emotions?: string[], domain?: string, freeText?: string) => {
    setFlowState((prev) => ({
      ...prev,
      phase: 'chatting',
      currentMacroStage: 'identification',
    }));
    setIsLoading(true);

    try {
      const parts = [
        emotions?.length ? `אני מרגיש: ${emotions.join(', ')}` : '',
        domain ? `בתחום: ${domain}` : '',
        freeText?.trim() ? freeText.trim() : '',
      ].filter(Boolean);
      const contextMessage = parts.join('. ') || 'אני רוצה להתחיל';

      const convId = await createConversation(language, getToken);
      setConversationId(convId);

      const response = await sendMessageV3(contextMessage, convId, language, getToken);

      const assistantMsg: V3ChatMessage = {
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

      // Check for tool_call on opening
      if (response.tool_call) {
        const tool = toolCallToActiveTool(response.tool_call);
        if (tool) setActiveTool(tool);
      }
    } catch (err) {
      console.error('[V3 Chat] startOnboarding error:', err);
      setMessages([{
        id: `a-opening-${Date.now()}`,
        role: 'assistant',
        content: 'ספר לי קצת על מה שעובר עליך בתקופה הזו?',
        phase: 'S1',
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [language, getToken]);

  // ---------------------------------------------------------------------------
  // Stage transitions (same as V2)
  // ---------------------------------------------------------------------------
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
      const intro: StageIntroPayload = await fetchStageIntro(conversationId, nextStageId, language, getToken);
      setFlowState((prev) => ({
        ...prev,
        phase: 'answering_intro',
        introPayload: intro,
      }));
    } catch {
      setFlowState((prev) => ({ ...prev, phase: 'chatting' }));
    }
  }, [conversationId, flowState.summary, flowState.currentMacroStage, language, getToken]);

  const submitIntroAnswers = useCallback(
    async (answers: Record<string, string[]>) => {
      if (!conversationId) return;
      const macroStage = flowState.currentMacroStage;

      setFlowState((prev) => ({ ...prev, phase: 'submitting_answers' }));

      try {
        const result = await submitStageIntroAnswers(conversationId, macroStage, answers, language, getToken);

        const openingContent = result.opening_message
          || (language === 'he' ? 'בוא נתחיל את השלב הבא. ספר לי מה עובר עליך.' : "Let's start the next stage.");
        const firstStep = macroStage === 'discovery' ? 'S9' : macroStage === 'kamaz' ? 'S12' : macroStage === 'choice' ? 'S13' : 'S14';

        const openingMsg: V3ChatMessage = {
          id: `a-stage-open-${Date.now()}`,
          role: 'assistant',
          content: openingContent,
          phase: firstStep,
        };

        setMessages([openingMsg]);

        // V3: check for tool_call in stage-intro response
        if (result.tool_call) {
          const tool = toolCallToActiveTool(result.tool_call as Record<string, unknown>);
          if (tool) setActiveTool(tool);
        } else {
          setActiveTool(null);
        }

        setFlowState((prev) => ({
          ...prev,
          phase: 'chatting',
          introPayload: undefined,
          summary: undefined,
          currentStep: firstStep,
          currentMacroStage: macroStage,
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
      setMessages(data.messages as V3ChatMessage[]);
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
      console.error('[V3 Chat] resumeConversation error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [getToken]);

  const startNewConversation = useCallback(() => {
    clearSession();
    setMessages([]);
    setConversationId(null);
    setCollectedData({});
    setSaturationScore(0);
    setActiveTool(null);
    setFlowState({
      phase: 'onboarding',
      currentMacroStage: 'identification',
      currentStep: 'S0',
    });
  }, []);

  // ---------------------------------------------------------------------------
  // Initialization (same as V2)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!isSignedIn) return;
    let cancelled = false;

    const saved = loadSession();
    if (saved && saved.conversationId && saved.messages.length > 0) {
      setConversationId(saved.conversationId);
      setMessages(saved.messages);
      setCollectedData(saved.collectedData || {});
      setSaturationScore(saved.saturationScore || 0);
      setFlowState(saved.flowState);
      return;
    }

    const timeout = setTimeout(() => {
      if (!cancelled) {
        setFlowState((prev) => prev.phase === 'initializing' ? { ...prev, phase: 'onboarding' } : prev);
      }
    }, 10_000);

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

    return () => { cancelled = true; clearTimeout(timeout); };
  }, [getToken, isSignedIn]);

  return {
    flowState,
    messages,
    conversationId,
    isLoading,
    saturationScore,
    collectedData,
    quotaExceeded,
    dismissQuotaExceeded: () => setQuotaExceeded(false),
    sendMessage,
    startOnboarding,
    startNewConversation,
    resumeConversation,
    requestNextStageIntro,
    submitIntroAnswers,
    // V3-specific
    activeTool,
    toolSubmitting,
    submitTool,
    dismissTool,
  };
}
