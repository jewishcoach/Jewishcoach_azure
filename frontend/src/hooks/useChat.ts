import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import type { Message, Conversation, ToolCall } from '../types';
import { apiClient } from '../services/api';
import { BSD_VERSION, getBsdEndpoint } from '../config';

export const useChat = (displayName?: string | null) => {
  const { t, i18n } = useTranslation();
  
  // In demo mode, we don't have Clerk user - use displayName directly
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
      
      // Add welcome message with animation delay
      setTimeout(() => {
        // Get user's display name, fall back to Clerk name
        const userName = displayName || user?.firstName || user?.fullName?.split(' ')[0] || '';
        
        // Create greeting with name
        let greeting: string;
        if (userName) {
          if (i18n.language === 'he') {
            greeting = `שלום ${userName} ${t('welcome_message')}`;
          } else {
            greeting = `Hello ${userName} ${t('welcome_message')}`;
          }
        } else {
          // Fallback if no name available
          if (i18n.language === 'he') {
            greeting = `שלום ${t('welcome_message')}`;
          } else {
            greeting = `Hello ${t('welcome_message')}`;
          }
        }
        
        const welcomeMessage: Message = {
          id: Date.now(),
          role: 'assistant',
          content: greeting,
          timestamp: new Date().toISOString(),
        };
        setMessages([welcomeMessage]);
        setLoading(false); // Ensure loading is off after welcome message
      }, 500); // Small delay for animation
    }
  }, [hasInitialized, messages.length, conversationId, t, i18n.language, user, displayName]);

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
      
      // Filter out metadata from message content
      const cleanMessages = (conv.messages || []).map(msg => {
        // Clean metadata from assistant messages
        if (msg.role === 'assistant') {
          let cleanContent = msg.content;
          
          // Remove metadata patterns
          cleanContent = cleanContent.replace(/\n\n__METADATA__:.*$/s, '');
          cleanContent = cleanContent.replace(/__SOURCES__:.*$/s, '');
          cleanContent = cleanContent.replace(/\n\n\{.*"sources".*\}$/s, '');
          
          return {
            ...msg,
            content: cleanContent.trim()
          };
        }
        return msg;
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
    
    // Get user's display name, fall back to Clerk name
    const userName = displayName || user?.firstName || user?.fullName?.split(' ')[0] || '';
    
    // Create greeting with name
    let greeting: string;
    if (userName) {
      if (i18n.language === 'he') {
        greeting = `שלום ${userName} ${t('welcome_message')}`;
      } else {
        greeting = `Hello ${userName} ${t('welcome_message')}`;
      }
    } else {
      // Fallback if no name available
      if (i18n.language === 'he') {
        greeting = `שלום ${t('welcome_message')}`;
      } else {
        greeting = `Hello ${t('welcome_message')}`;
      }
    }
    
    // Add welcome message immediately to prevent visual "jump"
    const welcomeMessage: Message = {
      id: Date.now(),
      role: 'assistant',
      content: greeting,
      timestamp: new Date().toISOString(),
    };
    
    setMessages([welcomeMessage]);
    setConversationId(null);
    setCurrentPhase('S0');
    setActiveTool(null); // NEW: Clear active tool for new conversation
    setHasInitialized(true); // Mark as initialized to prevent duplicate welcome
    setLoading(false); // Ensure loading is off
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
        
        const response = await fetch(
          getBsdEndpoint(currentConvId!, 'v2'),  // currentConvId is guaranteed to be set
          {
            method: 'POST',
            credentials: 'include',
            headers: { 
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ 
              message: content, 
              conversation_id: currentConvId,
              language 
            }),
          }
        );

        if (!response.ok) {
          throw new Error('Failed to send message (V2)');
        }

        const data = await response.json();
        console.log('✅ [BSD V2] Response:', data);

        // Simulate streaming for smooth UX
        const assistantContent = data.coach_message;
        const assistantMessageId = Date.now() + 1;
        
        // Add message character by character (simulated streaming)
        let currentText = '';
        const words = assistantContent.split(' ');
        
        for (let i = 0; i < words.length; i++) {
          currentText += (i > 0 ? ' ' : '') + words[i];
          
          setMessages(prev => {
            const newMessages = [...prev];
            const existingIndex = newMessages.findIndex(
              msg => msg.role === 'assistant' && msg.id === assistantMessageId
            );
            
            const newMessage = {
              id: assistantMessageId,
              role: 'assistant' as const,
              content: currentText,
              timestamp: new Date().toISOString(),
            };
            
            if (existingIndex !== -1) {
              newMessages[existingIndex] = newMessage;
            } else {
              newMessages.push(newMessage);
            }
            
            return newMessages;
          });
          
          // Small delay for typing effect
          await new Promise(resolve => setTimeout(resolve, 30));
        }
        
        // Update phase
        if (data.current_step) {
          setCurrentPhase(data.current_step);
        }
        
        // Call completion callback
        if (onResponseComplete && assistantContent.trim()) {
          onResponseComplete(assistantContent.trim());
        }
        
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
                      
                      // Clean the content before displaying (remove any metadata that might have slipped through)
                      let displayContent = assistantContent;
                      displayContent = displayContent.replace(/\n\nMETADATA:.*$/s, '');
                      displayContent = displayContent.replace(/\n\n__METADATA__:.*$/s, '');
                      displayContent = displayContent.replace(/__SOURCES__:.*$/s, '');
                      displayContent = displayContent.replace(/METADATA:.*$/s, '');
                      displayContent = displayContent.trim();
                      
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
                  
                  // Update current phase if provided
                  if (data.current_phase) {
                    console.log('🔄 Updating phase:', currentPhase, '->', data.current_phase);
                    setCurrentPhase(data.current_phase);
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
      // Add error message with more details
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setMessages(prev => [...prev, {
        id: Date.now() + 2,
        role: 'assistant',
        content: `מצטער, היתה שגיאה בעיבוד ההודעה. (${errorMessage})`,
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
