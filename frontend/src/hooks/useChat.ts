import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useUser } from '@clerk/clerk-react';
import type { Message, Conversation, ToolCall } from '../types';
import { apiClient } from '../services/api';
import { BSD_VERSION, getBsdEndpoint } from '../config';
import { stripUndefined } from '../utils/messageContent';

/** Safe name for greeting - never undefined, never literal "undefined" */
function getNameForGreeting(displayName?: string | null, clerkFirstName?: string | null, lang: string = 'he'): string {
  const raw = displayName ?? clerkFirstName ?? '';
  const cleaned = (typeof raw === 'string' ? raw : '').replace(/^undefined$/i, '').trim();
  if (cleaned) return cleaned;
  return lang === 'he' ? 'רב' : 'there';
}

export const useChat = (displayName?: string | null) => {
  const { t, i18n } = useTranslation();
  const { user: clerkUser } = useUser();
  
  // In demo mode, displayName is passed directly; otherwise use displayName from API or Clerk
  const user = displayName ? { firstName: displayName } : null;
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string>('S0');
  const [activeTool, setActiveTool] = useState<ToolCall | null>(null); // NEW: Track active tool from backend
  const [hasInitialized, setHasInitialized] = useState(false);
  const streamingMessageIdRef = useRef<number | null>(null); // Track current streaming message

  // Auto-send welcome message on mount (only on first load)
  useEffect(() => {
    if (!hasInitialized && messages.length === 0 && conversationId === null) {
      setHasInitialized(true);
      setLoading(false); // Clear loading state on initial load

      // Pre-warm prompt cache for faster first coach response
      apiClient.warmupCache();

      // Add welcome message with animation delay
      setTimeout(() => {
        const name = getNameForGreeting(displayName, clerkUser?.firstName, i18n.language);
        const greeting = stripUndefined(String(t('welcome_message', { name }) ?? ''));

        const welcomeMessage: Message = {
          id: Date.now(),
          role: 'assistant',
          content: greeting,
          timestamp: new Date().toISOString(),
          meta: { phase: 'S0' },
        };
        setMessages([welcomeMessage]);
        setLoading(false); // Ensure loading is off after welcome message
      }, 500); // Small delay for animation
    }
  }, [hasInitialized, messages.length, conversationId, t, i18n.language, user, displayName, clerkUser?.firstName]);

  const createConversation = async () => {
    const response = await apiClient.createConversation();
    setConversationId(response.id);
    setCurrentPhase(response.current_phase || 'S0');
    return response;
  };

  const loadConversation = async (conversationId: number) => {
    try {
      setLoading(false); // Clear any loading state when switching conversations
      const conv = await apiClient.getConversation(conversationId);
      
      // Filter out metadata and undefined from all messages; enrich phase for smart scroll
      const currentPhase = conv.current_phase || 'S0';
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
          meta = { ...meta, phase: currentPhase };
        }
        return { ...msg, content: cleanContent, meta };
      });
      
      setMessages(cleanMessages);
      setCurrentPhase(conv.current_phase || 'S0');
      setConversationId(conversationId);
      setActiveTool(null); // NEW: Clear active tool when loading different conversation
      setHasInitialized(true);
      setLoading(false); // Ensure loading is off
    } catch (error) {
      console.error('Error loading conversation:', error);
      setLoading(false); // Clear loading state on error
    }
  };

  const startNewConversation = async () => {
    setLoading(false); // Clear any loading state when starting new chat
    
    const name = getNameForGreeting(displayName, clerkUser?.firstName, i18n.language);
    const greeting = stripUndefined(String(t('welcome_message', { name }) ?? ''));

    // Add welcome message immediately to prevent visual "jump"
    const welcomeMessage: Message = {
      id: Date.now(),
      role: 'assistant',
      content: greeting,
      timestamp: new Date().toISOString(),
      meta: { phase: 'S0' },
    };
    
    setMessages([welcomeMessage]);
    setConversationId(null);
    setCurrentPhase('S0');
    setActiveTool(null); // NEW: Clear active tool for new conversation
    setHasInitialized(true); // Mark as initialized to prevent duplicate welcome
    setLoading(false); // Ensure loading is off

    // Pre-warm prompt cache for faster first coach response
    apiClient.warmupCache();
  };

  const sendMessage = async (
    content: string, 
    language: string, 
    token: string,
    onResponseComplete?: (responseText: string) => void  // NEW: Optional callback for voice mode
  ) => {
    // Ensure we have a conversation ID
    let currentConvId = conversationId;
    if (!currentConvId) {
      const conv = await createConversation();
      currentConvId = conv.id;
    }

    setLoading(true);
    
    // Add user message immediately
    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    try {
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
          body: JSON.stringify({ message: content, conversation_id: currentConvId, language }),
        });

        if (!response.ok) {
          const errBody = await response.text();
          console.error('[BSD V2] Error response:', response.status, errBody);

          // Auto-recover: if conversation was lost (e.g. server restart), create new one and retry once
          if (response.status === 404 && errBody.includes('Conversation not found') && currentConvId === conversationId) {
            console.warn('[BSD V2] Conversation not found — creating new conversation and retrying...');
            try {
              const newConv = await createConversation();
              const retryUrl = getBsdEndpoint(newConv.id, 'v2');
              const retryResponse = await fetch(retryUrl, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ message: content, conversation_id: newConv.id, language }),
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
                if (retryData.tool_call) setActiveTool(retryData.tool_call);
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
        setMessages(prev => [...prev, {
          id: assistantMessageId,
          role: 'assistant',
          content: coachContent,
          timestamp: new Date().toISOString(),
          meta: { phase: step },
        }]);
        if (data.current_step) setCurrentPhase(data.current_step);
        if (data.tool_call) {
          console.log('🛠️ [BSD V2] Activating tool:', data.tool_call);
          setActiveTool(data.tool_call);
        }
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
                    setActiveTool(data.tool_call);
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
      const isHebrew = i18n.language === 'he' || i18n.language?.startsWith('he');
      let userFacingMessage: string;
      if (errorCode.includes('V2_ERROR_404') || errorCode.includes('V2_ERROR_401')) {
        userFacingMessage = isHebrew
          ? 'השיחה לא נמצאה. לחץ על "שיחה חדשה" כדי להתחיל מחדש.'
          : 'Session not found. Please start a new conversation.';
      } else if (errorCode.includes('V2_ERROR_429_QUOTA')) {
        userFacingMessage = isHebrew
          ? 'הגעת למגבלת ההודעות שלך לחודש זה.\n\n[➡ לשדרוג תוכנית](/billing)'
          : 'You have reached your monthly message limit.\n\n[➡ Upgrade your plan](/billing)';
      } else if (errorCode.includes('V2_ERROR_429')) {
        userFacingMessage = isHebrew
          ? 'שולחים הודעות מהר מדי. המתן רגע ונסה שוב.'
          : 'Sending messages too fast. Please wait a moment and try again.';
      } else if (errorCode.includes('V2_ERROR_5') || errorCode.includes('NetworkError') || errorCode.includes('Failed to fetch') || errorCode.includes('Network Error')) {
        userFacingMessage = isHebrew
          ? 'אירעה שגיאה בשרת. נסה שוב בעוד רגע.'
          : 'Server error. Please try again in a moment.';
      } else {
        userFacingMessage = isHebrew
          ? 'מצטער, אירעה שגיאה. נסה שוב.'
          : 'Sorry, something went wrong. Please try again.';
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

  const clearMessages = () => {
    setMessages([]);
    setConversationId(null);
    setHasInitialized(false);
  };

  return { 
    messages, 
    loading,
    currentPhase,
    conversationId,
    activeTool, // NEW: Return active tool for InsightHub
    sendMessage,
    loadConversation,
    startNewConversation,
    createConversation
  };
};
