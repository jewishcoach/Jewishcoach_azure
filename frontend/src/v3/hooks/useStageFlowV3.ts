import { useCallback, useEffect, useRef, useState } from 'react';
import { useV3Auth } from './useV3Auth';
import type {
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
  ToolValidationError,
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
  activeTool?: ActiveInlineTool | null;
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
  const { getToken, isSignedIn } = useV3Auth();
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
  const sendingRef = useRef(false);
  // Next stage's intro questions, fetched in the background as soon as the stage ends (the LLM call takes
  // ~12-16s; the user is reading the closing message + summary meanwhile)
  const introPrefetchRef = useRef<{ stageId: string; promise: Promise<StageIntroPayload | null> } | null>(null);

  // ---------------------------------------------------------------------------
  // Send chat message
  // ---------------------------------------------------------------------------
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading || sendingRef.current) return;
      sendingRef.current = true;
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
          safety: response.safety ?? undefined,
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
          // Let the user read the coach's closing message before the summary screen covers it
          setFlowState((prev) => ({ ...prev, pendingSummary: response.stage_complete as StageSummaryPayload }));
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
        sendingRef.current = false;
        setIsLoading(false);
      }
    },
    [conversationId, language, getToken, isLoading],
  );

  // ---------------------------------------------------------------------------
  // Submit inline tool
  // ---------------------------------------------------------------------------
  const submitTool = useCallback(
    async (toolType: string, data: Record<string, unknown>) => {
      if (!conversationId || toolSubmitting) return;
      setToolSubmitting(true);

      try {
        const response = await submitToolResponse(conversationId, toolType, data, getToken);

        // Only now replace the card with its completed version — on failure the card stays
        // mounted with the user's input intact so they can fix and resend.
        const toolMsg: V3ChatMessage = {
          id: `t-${Date.now()}`,
          role: 'tool_result',
          content: '',
          toolResult: { tool_type: toolType, data },
        };
        setMessages((prev) => [...prev, toolMsg]);
        setActiveTool(null);

        if (response.coach_message) {
          const assistantMsg: V3ChatMessage = {
            id: `a-${Date.now()}`,
            role: 'assistant',
            content: response.coach_message,
            phase: response.current_step ?? undefined,
            suggestions: response.suggestions,
            safety: response.safety ?? undefined,
          };
          setMessages((prev) => [...prev, assistantMsg]);
        }
        if (response.saturation_score != null) {
          setSaturationScore(response.saturation_score);
        }

        if (response.collected_data) {
          setCollectedData((prev) => ({ ...prev, ...response.collected_data }));
        }

        const newStep = response.current_step;
        if (newStep) {
          setFlowState((prev) => ({
            ...prev,
            currentStep: newStep,
            currentMacroStage: stepToMacroStage(newStep),
          }));
        }

        // Check for chained tool_call
        const nextTool = response.tool_call
          ? toolCallToActiveTool(response.tool_call as unknown as Record<string, unknown>)
          : null;
        if (nextTool) setActiveTool(nextTool);

        // A card can be the step that ends a macro-stage (e.g. declaration/commitment card)
        if (response.stage_complete) {
          // Let the user read the coach's closing message before the summary screen covers it
          setFlowState((prev) => ({ ...prev, pendingSummary: response.stage_complete as StageSummaryPayload }));
        }

      } catch (err) {
        if (!(err instanceof ToolValidationError)) console.error('[V3 Chat] submitTool error:', err);
        setMessages((prev) => [...prev, {
          id: `e-${Date.now()}`,
          role: 'assistant',
          content: err instanceof ToolValidationError ? err.message : 'סליחה, משהו השתבש. נסה שוב בבקשה.',
        }]);
      } finally {
        setToolSubmitting(false);
      }
    },
    [conversationId, toolSubmitting, getToken, activeTool, flowState.currentStep],
  );

  const showStageSummary = useCallback(() => {
    setFlowState((prev) => (prev.pendingSummary
      ? { ...prev, phase: 'stage_complete', summary: prev.pendingSummary, pendingSummary: undefined }
      : prev));
  }, []);

  // ---------------------------------------------------------------------------
  // Dismiss tool (skip to chat)
  // ---------------------------------------------------------------------------
  const dismissTool = useCallback(() => {
    setActiveTool(null);
  }, []);

  // ---------------------------------------------------------------------------
  // Open a conversation with its first message (onboarding line / couple process)
  // ---------------------------------------------------------------------------
  const openConversation = useCallback(async (getConversationId: () => Promise<number>, contextMessage: string) => {
    setFlowState((prev) => ({
      ...prev,
      phase: 'chatting',
      currentMacroStage: 'identification',
    }));
    setIsLoading(true);

    try {
      const convId = await getConversationId();
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

      if (response.current_step) {
        setFlowState((prev) => ({
          ...prev,
          currentStep: response.current_step,
          currentMacroStage: stepToMacroStage(response.current_step || prev.currentStep || 'S0'),
        }));
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

  // Start onboarding — V3 accepts optional freeText
  const startOnboarding = useCallback((emotions?: string[], domain?: string, freeText?: string) => {
    const parts = [
      // the options already read "אני מרגיש(ה) …" — "אני מרגיש: אני מרגיש תקוע" doubled it in the topic
      emotions?.length ? (/^(אני|קשה)/.test(emotions[0]) ? emotions.join(', ') : `אני מרגיש: ${emotions.join(', ')}`) : '',
      domain ? `בתחום: ${domain}` : '',
      freeText?.trim() ? freeText.trim() : '',
    ].filter(Boolean);
    return openConversation(() => createConversation(language, getToken), parts.join('. ') || 'אני רוצה להתחיל');
  }, [openConversation, language, getToken]);

  // Couple process: the member's conversation already exists (created with the shared event)
  const startConversationWith = useCallback((convId: number, contextMessage: string) => {
    clearSession();
    setMessages([]);
    setCollectedData({});
    setSaturationScore(0);
    setActiveTool(null);
    return openConversation(async () => convId, contextMessage);
  }, [openConversation]);

  // ---------------------------------------------------------------------------
  // Stage transitions (same as V2)
  // ---------------------------------------------------------------------------
  const endedStageSummary = flowState.pendingSummary ?? (flowState.phase === 'stage_complete' ? flowState.summary : undefined);
  useEffect(() => {
    const nextId = endedStageSummary?.next_stage_id;
    if (!conversationId || !nextId || introPrefetchRef.current?.stageId === nextId) return;
    introPrefetchRef.current = {
      stageId: nextId,
      promise: fetchStageIntro(conversationId, nextId, language, getToken).catch(() => null),
    };
  }, [conversationId, endedStageSummary?.next_stage_id, language, getToken]);
  const savePersonalStatement = useCallback(async (personalStatement?: string) => {
    if (!conversationId || !personalStatement) return;
    try {
      const base = getApiBase();
      const token = await getToken();
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers.Authorization = `Bearer ${token}`;
      await fetch(`${base}/chat/v2/conversations/${conversationId}/statement`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ stage_id: flowState.currentMacroStage, statement: personalStatement }),
      });
    } catch { /* best effort */ }
  }, [conversationId, flowState.currentMacroStage, getToken]);

  /** The intro of a macro-stage — after a stage summary, or after the couple mirror screen (כמ"ז) */
  const goToStage = useCallback(async (nextStageId: string) => {
    if (!conversationId) return;
    setFlowState((prev) => ({
      ...prev,
      phase: 'loading_intro',
      currentMacroStage: nextStageId,
    }));

    try {
      const prefetched = introPrefetchRef.current?.stageId === nextStageId ? await introPrefetchRef.current.promise : null;
      introPrefetchRef.current = null;
      const intro: StageIntroPayload = prefetched ?? await fetchStageIntro(conversationId, nextStageId, language, getToken);
      setFlowState((prev) => ({
        ...prev,
        phase: 'answering_intro',
        introPayload: intro,
      }));
    } catch {
      setFlowState((prev) => ({ ...prev, phase: 'chatting' }));
    }
  }, [conversationId, language, getToken]);

  const requestNextStageIntro = useCallback(async (personalStatement?: string) => {
    if (!conversationId || !flowState.summary?.next_stage_id) return;
    await savePersonalStatement(personalStatement);
    await goToStage(flowState.summary.next_stage_id);
  }, [conversationId, flowState.summary, savePersonalStatement, goToStage]);

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
      // the card the coach announced ("עכשיו נבדוק יחד מה הפער…") — without it a fresh window had nothing to answer
      setActiveTool(data.pending_tool_call ? toolCallToActiveTool(data.pending_tool_call) : null);
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
  // Persist session on every state change — a reload must restore exactly what the user saw
  // (stage transitions, intro answers and onboarding used to skip saving → stale screen on reload).
  // Transient phases are saved as the stable screen they came from.
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!conversationId || messages.length === 0) return;
    const { phase } = flowState;
    if (phase === 'initializing' || phase === 'onboarding' || phase === 'welcome_back') return;
    const stablePhase =
      phase === 'loading_intro' ? 'stage_complete'
        : phase === 'submitting_answers' ? 'answering_intro'
          : phase;
    saveSession({
      conversationId,
      flowState: { ...flowState, phase: stablePhase },
      messages,
      collectedData,
      saturationScore,
      activeTool,
    });
  }, [conversationId, flowState, messages, collectedData, saturationScore, activeTool]);

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
      if (saved.activeTool) setActiveTool(saved.activeTool);
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
    showStageSummary,
    startOnboarding,
    startNewConversation,
    resumeConversation,
    requestNextStageIntro,
    submitIntroAnswers,
    // couple process
    startConversationWith,
    goToStage,
    savePersonalStatement,
    // V3-specific
    activeTool,
    toolSubmitting,
    submitTool,
    dismissTool,
  };
}
