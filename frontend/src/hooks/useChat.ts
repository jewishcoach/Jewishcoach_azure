import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useUser } from '@clerk/clerk-react';
import type { Message, Conversation, ToolCall, StationCheckpointPayload } from '../types';
import { isChatBlockedByActiveTool } from '../utils/activeFormTools';
import { apiClient, normalizeConversationId } from '../services/api';
import { BSD_VERSION, getBsdEndpoint } from '../config';
import { stripUndefined } from '../utils/messageContent';
import { getWorkspaceWelcomeMessage, type TraineeGender } from '../utils/welcomeMessage';
import {
  WORKSPACE_WELCOME_CHAR_MS,
  WORKSPACE_WELCOME_CHARS_PER_TICK,
  revealTypedBlock,
  sleep,
} from '../utils/staggeredTyping';

function isWorkspaceWelcomeOnly(msgs: Message[]): boolean {
  if (msgs.length === 0 || msgs.length > 3) return false;
  return msgs.every((m) => m.role === 'assistant' && m.meta?.phase === 'S0');
}

export const useChat = (
  displayName?: string | null,
  chatProfileReady = true,
  traineeGender: TraineeGender | null = null,
) => {
  const { t, i18n } = useTranslation();
  const { user: clerkUser } = useUser();

  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  /** Fetching past messages when opening a conversation from archive (separate from assistant "thinking"). */
  const [historyLoading, setHistoryLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string>('S0');
  const [activeTool, setActiveTool] = useState<ToolCall | null>(null); // NEW: Track active tool from backend
  const activeToolRef = useRef<ToolCall | null>(null);
  const [hasInitialized, setHasInitialized] = useState(false);
  const [quotaExceeded, setQuotaExceeded] = useState(false);
  const [stationCheckpoint, setStationCheckpoint] = useState<StationCheckpointPayload | null>(null);
  /** True while a station gate is active — blocks free-text send until «Continue coaching». */
  const stationGateRef = useRef(false);
  useEffect(() => {
    stationGateRef.current = Boolean(stationCheckpoint);
  }, [stationCheckpoint]);
  const streamingMessageIdRef = useRef<number | null>(null); // Track current streaming message
  const welcomeAbortRef = useRef<AbortController | null>(null);
  const [welcomeOpeningBusy, setWelcomeOpeningBusy] = useState(false);
  const [welcomeTypingText, setWelcomeTypingText] = useState<string | null>(null);
  /** Full welcome copy while `welcomeTypingText` is partial — fixes bubble width during reveal. */
  const [welcomeTypingLayoutText, setWelcomeTypingLayoutText] = useState<string | null>(null);

  const playWelcomeSequence = useCallback(async () => {
    welcomeAbortRef.current?.abort();
    const ac = new AbortController();
    welcomeAbortRef.current = ac;
    setWelcomeOpeningBusy(true);
    setWelcomeTypingText(null);
    setWelcomeTypingLayoutText(null);
    setMessages([]);
    setLoading(false);

    const welcomeText = getWorkspaceWelcomeMessage(
      displayName,
      clerkUser?.firstName,
      i18n.language,
      t,
      traineeGender,
    );

    try {
      await sleep(300, ac.signal);
      if (ac.signal.aborted) return;
      setWelcomeTypingLayoutText(welcomeText);
      setWelcomeTypingText('');
      await revealTypedBlock(
        welcomeText,
        (partial) => {
          if (!ac.signal.aborted) setWelcomeTypingText(partial);
        },
        ac.signal,
        {
          charMs: WORKSPACE_WELCOME_CHAR_MS,
          charsPerTick: WORKSPACE_WELCOME_CHARS_PER_TICK,
        },
      );
      if (ac.signal.aborted) return;
      setMessages([
        {
          id: Date.now(),
          role: 'assistant',
          content: welcomeText,
          timestamp: new Date().toISOString(),
          meta: { phase: 'S0' },
        },
      ]);
      setWelcomeTypingText(null);
      setWelcomeTypingLayoutText(null);
    } finally {
      if (!ac.signal.aborted) {
        setWelcomeOpeningBusy(false);
        setWelcomeTypingText(null);
        setWelcomeTypingLayoutText(null);
      }
    }
  }, [displayName, clerkUser?.firstName, i18n.language, t, traineeGender]);

  useEffect(() => {
    return () => {
      welcomeAbortRef.current?.abort();
    };
  }, []);

  // Staggered workspace welcome once profile is ready (avoid Clerk name before /users/me returns)
  useEffect(() => {
    if (!chatProfileReady) return;
    if (!hasInitialized && messages.length === 0 && conversationId === null) {
      setHasInitialized(true);
      void apiClient.warmupCache(i18n.language);
      void playWelcomeSequence();
    }
  }, [
    hasInitialized,
    messages.length,
    conversationId,
    chatProfileReady,
    playWelcomeSequence,
    i18n.language,
  ]);

  /** When display_name loads or changes, refresh welcome-only bubbles (not mid-sequence). */
  useEffect(() => {
    if (!chatProfileReady || conversationId !== null || welcomeOpeningBusy) return;
    setMessages((prev) => {
      if (!isWorkspaceWelcomeOnly(prev)) return prev;
      const welcomeText = getWorkspaceWelcomeMessage(
        displayName,
        clerkUser?.firstName,
        i18n.language,
        t,
        traineeGender,
      );
      const prevJoined = prev.map((m) => m.content).join('\n\n');
      if (prevJoined === welcomeText) return prev;
      return [
        {
          id: prev[0]?.id ?? Date.now(),
          role: 'assistant' as const,
          content: welcomeText,
          timestamp: prev[0]?.timestamp ?? new Date().toISOString(),
          meta: { phase: 'S0' as const },
        },
      ];
    });
  }, [
    displayName,
    clerkUser?.firstName,
    chatProfileReady,
    conversationId,
    i18n.language,
    t,
    traineeGender,
    welcomeOpeningBusy,
  ]);

  useEffect(() => {
    activeToolRef.current = activeTool;
  }, [activeTool]);

  /** Keep ref in sync immediately so sendMessage cannot race before the next render. */
  const commitActiveTool = (tool: ToolCall | null) => {
    activeToolRef.current = tool;
    setActiveTool(tool);
  };

  const createConversation = async () => {
    const response = await apiClient.createConversation();
    setConversationId(response.id);
    setCurrentPhase(response.current_phase || 'S0');
    return response;
  };

  const loadConversation = async (convId: number) => {
    welcomeAbortRef.current?.abort();
    setWelcomeOpeningBusy(false);
    setWelcomeTypingText(null);
    setWelcomeTypingLayoutText(null);
    setHistoryLoading(true);
    setMessages([]);
    setConversationId(convId);
    try {
      const conv = await apiClient.getConversation(convId);

      // Filter out metadata and undefined from all messages; enrich phase for smart scroll
      const phaseNow = conv.current_phase || 'S0';
      const raw = conv.messages || [];
      const lastAssistantIdx = raw.map((m: Message) => m.role).lastIndexOf('assistant');
      const cleanMessages = raw.map((msg: Message, idx: number) => {
        let cleanContent = msg.content ?? '';
        cleanContent = cleanContent.replace(/\n\n__METADATA__:.*$/s, '');
        cleanContent = cleanContent.replace(/__SOURCES__:.*$/s, '');
        cleanContent = cleanContent.replace(/\n\n\{.*"sources".*\}$/s, '');
        cleanContent = stripUndefined(cleanContent);
        let meta = msg.meta ?? {};
        // Ensure last assistant message has phase for smart scroll (backend may not have saved it for older convs)
        if (msg.role === 'assistant' && !meta.phase && idx === lastAssistantIdx) {
          meta = { ...meta, phase: phaseNow };
        }
        return { ...msg, content: cleanContent, meta };
      });

      setMessages(cleanMessages);
      setCurrentPhase(conv.current_phase || 'S0');
      setConversationId(convId);
      const last = cleanMessages.length ? cleanMessages[cleanMessages.length - 1] : null;
      let restoredStation: StationCheckpointPayload | null = null;
      if (last?.role === 'assistant' && last.meta?.station_checkpoint) {
        restoredStation = last.meta.station_checkpoint;
      }
      setStationCheckpoint(restoredStation);
      commitActiveTool(null); // NEW: Clear active tool when loading different conversation
      setHasInitialized(true);
    } catch (error) {
      console.error('Error loading conversation:', error);
    } finally {
      setHistoryLoading(false);
    }
  };

  const startNewConversation = async () => {
    setLoading(false);
    setHistoryLoading(false);
    setConversationId(null);
    setCurrentPhase('S0');
    setStationCheckpoint(null);
    commitActiveTool(null);
    setHasInitialized(true);
    void apiClient.warmupCache(i18n.language);
    await playWelcomeSequence();
  };

  const applyToolResponse = (result: any) => {
    if (!result) {
      commitActiveTool(null);
      return;
    }

    const coachContent = stripUndefined(String(result.coach_message ?? ''));
    const step = result.current_step ?? currentPhase;

    if (coachContent.trim()) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: coachContent,
        timestamp: new Date().toISOString(),
        meta: { phase: step },
      }]);
    }

    if (result.current_step) setCurrentPhase(result.current_step);
    if (result.tool_call) commitActiveTool(result.tool_call);
    else commitActiveTool(null);
  };

  /** Token string, or Clerk-style getter so UI can show “thinking” before auth/network. */
  const sendMessage = async (
    content: string,
    language: string,
    tokenOrGetter: string | (() => Promise<string | null | undefined>),
    onResponseComplete?: (responseText: string) => void,
  ) => {
    if (isChatBlockedByActiveTool(activeToolRef.current)) {
      return;
    }

    if (stationGateRef.current) {
      return;
    }

    if (welcomeOpeningBusy) {
      return;
    }

    const isFirstUserTurn = messages.filter((m) => m.role === 'user').length === 0;

    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    let token: string;
    if (typeof tokenOrGetter === 'function') {
      const raw = await tokenOrGetter();
      if (!raw) {
        setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
        setLoading(false);
        return;
      }
      token = raw;
    } else {
      token = tokenOrGetter;
    }
    apiClient.setToken(token);

    try {
      let currentConvId = conversationId;
      if (!currentConvId) {
        const conv = await createConversation();
        currentConvId = conv.id;
      }

      const convNumeric = normalizeConversationId(currentConvId);
      if (convNumeric === null) {
        setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
        console.error('[useChat] Invalid conversation id after create:', currentConvId);
        return;
      }
      currentConvId = convNumeric;

      if (BSD_VERSION === 'v2' && isFirstUserTurn) {
        void apiClient.warmupCache(language);
      }

      // ═══════════════════════════════════════════════════════════════════
      // V2: Single-agent conversational coach (non-streaming)
      // ═══════════════════════════════════════════════════════════════════
      if (BSD_VERSION === 'v2') {
        console.log('🆕 [BSD V2] Sending message...');

        const url = getBsdEndpoint(currentConvId!, 'v2');
        const response = await fetch(url, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ message: content, conversation_id: convNumeric, language }),
        });

        if (!response.ok) {
          const errBody = await response.text();
          console.error('[BSD V2] Error response:', response.status, errBody);

          // Auto-recover: if conversation was lost (e.g. server restart), create new one and retry once
          if (response.status === 404 && errBody.includes('Conversation not found') && currentConvId === conversationId) {
            console.warn('[BSD V2] Conversation not found — creating new conversation and retrying...');
            try {
              const newConv = await createConversation();
              const retryCid = normalizeConversationId(newConv.id);
              if (retryCid === null) throw new Error('Invalid new conversation id');
              const retryUrl = getBsdEndpoint(retryCid, 'v2');
              const retryResponse = await fetch(retryUrl, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ message: content, conversation_id: retryCid, language }),
              });
              if (retryResponse.ok) {
                const retryData = await retryResponse.json();
                const coachContent = stripUndefined(String(retryData.coach_message ?? ''));
                const step = retryData.current_step ?? 'S0';
                setMessages(prev => [...prev, {
                  id: Date.now() + 1,
                  role: 'assistant',
                  content: coachContent,
                  timestamp: new Date().toISOString(),
                  meta: { phase: step },
                }]);
                if (retryData.current_step) setCurrentPhase(retryData.current_step);
                if (retryData.tool_call) commitActiveTool(retryData.tool_call);
                setStationCheckpoint(retryData.station_checkpoint ?? null);
                if (onResponseComplete && retryData.coach_message?.trim()) onResponseComplete(retryData.coach_message.trim());
                setLoading(false);
                return;
              }
            } catch (recoveryErr) {
              console.error('[BSD V2] Auto-recovery failed:', recoveryErr);
              // Fall through to V2_ERROR_404 message
            }
          }

          // For 429, embed quota info in error message so catch block can show the right message
          if (response.status === 429 && errBody.includes('quota_exceeded')) {
            throw new Error('V2_ERROR_429_QUOTA');
          }
          throw new Error(`V2_ERROR_${response.status}`);
        }

        const data = await response.json();
        const assistantMessageId = Date.now() + 1;
        const coachContent = stripUndefined(String(data.coach_message ?? ''));
        const step = data.current_step ?? currentPhase;
        const sc = data.station_checkpoint as StationCheckpointPayload | null | undefined;
        setMessages(prev => [...prev, {
          id: assistantMessageId,
          role: 'assistant',
          content: coachContent,
          timestamp: new Date().toISOString(),
          meta: { phase: step, ...(sc ? { station_checkpoint: sc } : {}) },
        }]);
        if (data.current_step) setCurrentPhase(data.current_step);
        if (data.tool_call) {
          console.log('🛠️ [BSD V2] Activating tool:', data.tool_call);
          commitActiveTool(data.tool_call);
        }
        setStationCheckpoint(sc ?? null);
        if (onResponseComplete && data.coach_message?.trim()) onResponseComplete(data.coach_message.trim());
        setLoading(false);
        return;
      }
      
      // ═══════════════════════════════════════════════════════════════════
      // V1: Multi-layer architecture (streaming)
      // ═══════════════════════════════════════════════════════════════════
      const response = await fetch(
        apiClient.getMessageStreamUrl(currentConvId!),  // currentConvId is guaranteed to be set
        {
          method: 'POST',
          credentials: 'include', // Enable CORS credentials
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ content, language }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';
      const assistantMessageId = Date.now() + 1;
      streamingMessageIdRef.current = assistantMessageId; // Store the streaming message ID
      let streamComplete = false; // Flag to track if stream is complete
      let firstChunkReceived = false; // Track if we got any content yet
      
      if (reader) {
        // Keep loading dots until first chunk arrives
        
        while (true && !streamComplete) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }
          
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.content) {
                  // Filter out metadata/sources - don't show to user
                  if (!data.content.startsWith('__SOURCES__') && 
                      !data.content.startsWith('__METADATA__') &&
                      !data.content.startsWith('METADATA') &&
                      !data.content.includes('"sources"') &&
                      !data.content.includes('"evaluation"')) {
                    
                    // Also filter out if content contains metadata at the end
                    let cleanChunk = data.content;
                    
                    // Remove any trailing metadata patterns
                    cleanChunk = cleanChunk.replace(/\n\nMETADATA:.*$/s, '');
                    cleanChunk = cleanChunk.replace(/\n\n__METADATA__:.*$/s, '');
                    cleanChunk = cleanChunk.replace(/__SOURCES__:.*$/s, '');
                    cleanChunk = cleanChunk.replace(/METADATA:.*$/s, '');
                    
                    // Only add if there's actual content left
                    if (cleanChunk.trim()) {
                      assistantContent += cleanChunk;
                      
                      // Hide loading dots when first real content arrives
                      if (!firstChunkReceived) {
                        firstChunkReceived = true;
                        setLoading(false);
                      }
                    }
                    
                    setMessages(prev => {
                      const newMessages = [...prev];
                      
                      // Clean the content before displaying (remove metadata + undefined)
                      let displayContent = assistantContent;
                      displayContent = displayContent.replace(/\n\nMETADATA:.*$/s, '');
                      displayContent = displayContent.replace(/\n\n__METADATA__:.*$/s, '');
                      displayContent = displayContent.replace(/__SOURCES__:.*$/s, '');
                      displayContent = displayContent.replace(/METADATA:.*$/s, '');
                      displayContent = stripUndefined(displayContent);
                      
                      // Find if we already have this streaming message
                      const existingIndex = newMessages.findIndex(
                        msg => msg.role === 'assistant' && msg.id === assistantMessageId
                      );
                      
                      if (existingIndex !== -1) {
                        // Update existing message
                        newMessages[existingIndex] = {
                          ...newMessages[existingIndex],
                          content: displayContent
                        };
                      } else {
                        // Add new message
                        newMessages.push({
                          id: assistantMessageId,
                          role: 'assistant',
                          content: displayContent,
                          timestamp: new Date().toISOString(),
                        });
                      }
                      
                      return newMessages;
                    });
                  } else {
                    // Store metadata separately if needed (for debugging)
                    console.log('📊 Metadata received:', data.content.substring(0, 100) + '...');
                  }
                }
                
                if (data.done === true) {
                  // Message complete
                  console.log('✅ Message complete. Phase info:', data);
                  setLoading(false); // Stop loading animation immediately
                  streamingMessageIdRef.current = null; // Clear streaming message ID
                  streamComplete = true; // Mark stream as complete to exit while loop
                  
                  const step = data.current_phase ?? data.current_step;
                  if (step) {
                    setCurrentPhase(step);
                    // Store phase on the assistant message for smart scroll
                    setMessages(prev => {
                      const next = [...prev];
                      const idx = next.findIndex(m => m.role === 'assistant' && m.id === assistantMessageId);
                      if (idx !== -1) {
                        next[idx] = { ...next[idx], meta: { ...next[idx].meta, phase: step } };
                      }
                      return next;
                    });
                  }
                  
                  // NEW: Update active tool if provided (for Real-Time Reflection)
                  if (data.tool_call) {
                    console.log('🪞 Received tool_call:', data.tool_call);
                    commitActiveTool(data.tool_call);
                  }
                  
                  // Call callback with complete response (for voice mode TTS)
                  if (onResponseComplete && assistantContent.trim()) {
                    console.log('🔊 Triggering TTS callback with response');
                    onResponseComplete(assistantContent.trim());
                  }
                  
                  break; // Exit the for loop
                }
                
                // Also check for phase_changed (alternative completion signal)
                if (data.phase_changed !== undefined) {
                  console.log('📊 Phase update received:', data);
                  if (data.current_phase) {
                    console.log('🔄 Updating phase:', currentPhase, '->', data.current_phase);
                    setCurrentPhase(data.current_phase);
                  }
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e, 'Line:', line);
              }
            }
          }
        }
      }
      
      // Ensure loading is stopped even if we exit the loop
      setLoading(false);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorCode = error instanceof Error ? error.message : '';
      let userFacingMessage: string;
      if (errorCode.includes('V2_ERROR_404') || errorCode.includes('V2_ERROR_401')) {
        userFacingMessage = t('chat.errorSessionNotFound');
      } else if (errorCode.includes('V2_ERROR_429_QUOTA')) {
        setQuotaExceeded(true);
        return; // Modal will be shown by parent - no chat message
      } else if (errorCode.includes('V2_ERROR_429')) {
        userFacingMessage = t('chat.errorTooFast');
      } else if (errorCode.includes('V2_ERROR_5') || errorCode.includes('NetworkError') || errorCode.includes('Failed to fetch') || errorCode.includes('Network Error')) {
        userFacingMessage = t('chat.errorServer');
      } else {
        userFacingMessage = t('chat.errorGeneric');
      }
      setMessages(prev => [...prev, {
        id: Date.now() + 2,
        role: 'assistant',
        content: userFacingMessage,
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  /** User tapped «Continue coaching» on station card: persist intent, unlock chat, auto-send resume phrase for gentle coach turn. */
  const submitStationContinue = async (token: string) => {
    const cid = conversationId;
    if (cid === null || stationCheckpoint === null) return;
    await apiClient.sendStationIntent(cid, 'continue_coaching');
    stationGateRef.current = false;
    setStationCheckpoint(null);
    await sendMessage(t('chat.stationResumeUserPhrase'), i18n.language, token);
  };

  const clearMessages = () => {
    welcomeAbortRef.current?.abort();
    setWelcomeOpeningBusy(false);
    setWelcomeTypingText(null);
    setWelcomeTypingLayoutText(null);
    setMessages([]);
    setConversationId(null);
    setHasInitialized(false);
  };

  return { 
    messages, 
    loading,
    historyLoading,
    welcomeOpeningBusy,
    welcomeTypingText,
    welcomeTypingLayoutText,
    currentPhase,
    conversationId,
    activeTool,
    quotaExceeded,
    dismissQuotaModal: () => setQuotaExceeded(false),
    stationCheckpoint,
    submitStationContinue,
    sendMessage,
    loadConversation,
    startNewConversation,
    createConversation,
    applyToolResponse
  };
};
