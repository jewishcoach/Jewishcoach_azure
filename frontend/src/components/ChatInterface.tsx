import { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Send, Mic } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@clerk/clerk-react';
import { useChat } from '../hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { PhaseIndicator } from './PhaseIndicator';
import { Sidebar } from './Sidebar';
import { VoiceControlBar } from './VoiceControlBar';
import { InsightHub } from './InsightHub/InsightHub';
import { apiClient } from '../services/api';
import type { Conversation } from '../types';
import type { VoiceGender } from '../constants/voices';
import { isChatBlockedByActiveTool } from '../utils/activeFormTools';

interface ChatInterfaceProps {
  displayName?: string | null;
}

export const ChatInterface = ({ displayName }: ChatInterfaceProps) => {
  const { t, i18n } = useTranslation();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [inputValue, setInputValue] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [voiceGender, setVoiceGender] = useState<VoiceGender>('female');
  // Get activeTool from useChat instead of local state
  const { messages, loading, currentPhase, conversationId, activeTool, sendMessage, loadConversation, startNewConversation } = useChat(displayName);
  const chatLockedByForm = isChatBlockedByActiveTool(activeTool);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const speakFunctionRef = useRef<((text: string) => Promise<void>) | null>(null);
  const stopVoiceSessionRef = useRef<(() => void) | null>(null);
  const isSendingRef = useRef(false); // Prevent duplicate sends

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!chatLockedByForm || !isVoiceMode) return;
    if (stopVoiceSessionRef.current) stopVoiceSessionRef.current();
    setIsVoiceMode(false);
  }, [chatLockedByForm, isVoiceMode]);

  // Initialize: Get token and fetch conversations (after Clerk session is ready)
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;

    const init = async () => {
      try {
        const token = await getToken();
        if (token) {
          apiClient.setToken(token);
          const convs = await apiClient.getConversations();
          setConversations(convs);
        }
      } catch (error) {
        console.error('Error initializing:', error);
      }
    };
    init();
  }, [isLoaded, isSignedIn, getToken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Prevent duplicate submissions
    if (chatLockedByForm || !inputValue.trim() || loading || isSendingRef.current) {
      console.log('⚠️ Ignoring duplicate submit attempt');
      return;
    }

    const messageToSend = inputValue.trim();
    setInputValue('');
    isSendingRef.current = true; // Mark as sending
    
    try {
      console.log('📤 Sending message:', messageToSend.substring(0, 50));
      // getToken runs inside sendMessage so “coach thinking” shows immediately with the user bubble
      await sendMessage(messageToSend, i18n.language, getToken);

      const convs = await apiClient.getConversations();
      setConversations(convs);
      inputRef.current?.focus();
    } catch (error) {
      console.error('Error sending message:', error);
      inputRef.current?.focus();
    } finally {
      setTimeout(() => {
        isSendingRef.current = false;
      }, 300);
    }
  };

  const handleSelectConversation = async (id: number) => {
    // Stop voice mode if active when switching conversations
    if (isVoiceMode && stopVoiceSessionRef.current) {
      stopVoiceSessionRef.current();
      setIsVoiceMode(false);
    }
    await loadConversation(id);
  };

  const cleanAssistantContent = (content: string) => {
    let cleanContent = content;
    cleanContent = cleanContent.replace(/\n\n__METADATA__:.*$/s, '');
    cleanContent = cleanContent.replace(/__SOURCES__:.*$/s, '');
    cleanContent = cleanContent.replace(/\n\n\{.*"sources".*\}$/s, '');
    return cleanContent.trim();
  };

  const handleDeleteConversation = async (id: number) => {
    const confirmMessage = i18n.language === 'he'
      ? 'למחוק את השיחה הזו? פעולה זו לא ניתנת לשחזור.'
      : 'Delete this conversation? This action cannot be undone.';

    if (!window.confirm(confirmMessage)) {
      return;
    }

    try {
      const token = await getToken();
      if (!token) return;
      apiClient.setToken(token);
      await apiClient.deleteConversation(id);

      const convs = await apiClient.getConversations();
      setConversations(convs);

      if (conversationId === id) {
        await startNewConversation();
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  const handleShareConversation = async (id: number) => {
    try {
      const token = await getToken();
      if (!token) return;
      apiClient.setToken(token);
      const conv = await apiClient.getConversation(id);

      const title = conv.title || (i18n.language === 'he' ? 'שיחה' : 'Conversation');
      const createdAt = conv.created_at ? new Date(conv.created_at).toLocaleString() : '';
      const lines = [`${title}`, createdAt ? `(${createdAt})` : ''];

      const messagesText = (conv.messages || []).map((msg: { role: string; content?: string }) => {
        const roleLabel = msg.role === 'assistant'
          ? (i18n.language === 'he' ? 'מאמן' : 'Coach')
          : (i18n.language === 'he' ? 'אני' : 'User');
        const content = msg.role === 'assistant' ? cleanAssistantContent(msg.content ?? '') : (msg.content ?? '');
        return `${roleLabel}: ${content}`;
      });

      const shareText = lines.filter(Boolean).concat(messagesText).join('\n');
      await navigator.clipboard.writeText(shareText);

      const successMsg = i18n.language === 'he'
        ? 'השיחה הועתקה ללוח.'
        : 'Conversation copied to clipboard.';
      window.alert(successMsg);
    } catch (error) {
      console.error('Error sharing conversation:', error);
    }
  };

  const handleNewChat = async () => {
    // Stop voice mode if active when starting new chat
    if (isVoiceMode && stopVoiceSessionRef.current) {
      stopVoiceSessionRef.current();
      setIsVoiceMode(false);
    }
    await startNewConversation();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (chatLockedByForm) return;
      const form = e.currentTarget.form;
      if (form) form.requestSubmit();
    }
  };

  // Voice message sync handler - handles both user and AI messages for voice mode
  const handleVoiceMessage = useCallback(async (role: 'user' | 'assistant', content: string) => {
    console.log('🎤 Voice message sync:', role, content.substring(0, 50));
    
    if (role === 'user') {
      if (isChatBlockedByActiveTool(activeTool)) {
        return;
      }
      // Prevent duplicate sends (extra safety layer on top of useContinuousChat deduplication)
      if (isSendingRef.current) {
        console.log('⚠️ Voice: Already sending, ignoring duplicate');
        return;
      }
      
      isSendingRef.current = true;

      try {
        await sendMessage(content, i18n.language, getToken, (responseText) => {
          // This callback is called when the AI response streaming is complete
          console.log('🔊 AI response complete, triggering TTS:', responseText.substring(0, 50));
          if (speakFunctionRef.current) {
            speakFunctionRef.current(responseText);
          }
        });
      } catch (error) {
        console.error('Error in voice message:', error);
      } finally {
        setTimeout(() => {
          isSendingRef.current = false;
        }, 300);
      }
    }
  }, [getToken, i18n.language, sendMessage, activeTool]);

  const handleToolSubmit = async (submission: { tool_type: string; data: Record<string, unknown> }) => {
    if (!conversationId) return;

    try {
      const token = await getToken();
      if (!token) {
        console.error('No auth token available');
        return;
      }

      apiClient.setToken(token);
      await apiClient.submitToolResponse(conversationId, submission.tool_type, submission.data);
      
      // Note: We don't clear activeTool anymore - it's managed by useChat
      // Reflection widgets are read-only and update automatically
      
      // Refresh conversations to show updated history
      const convs = await apiClient.getConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Error submitting tool:', error);
    }
  };

  return (
    <div className="flex h-full w-full bg-cream">
      {/* LEFT: Insight Hub (Physical Left) */}
      <InsightHub
        conversationId={conversationId}
        currentPhase={currentPhase}
        activeTool={activeTool}
        onToolSubmit={handleToolSubmit}
      />

      {/* CENTER: Main Chat Area */}
      <div className="flex flex-col flex-1 h-full">
        {/* Phase Indicator */}
        <div className="px-4 pt-4">
          <PhaseIndicator currentPhase={currentPhase} language={i18n.language} />
        </div>

      {/* Messages Area - Glass Container */}
      <div className="flex-1 overflow-y-auto px-2 py-6">
        <div className="w-full">
          {messages.length === 0 ? (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center h-full text-center py-20"
            >
              <img src="/bsd-logo.png" alt="BSD אימון יהודי" className="h-20 mb-4 object-contain" />
              <p className="text-gray-600 max-w-md">
                {i18n.language === 'he' 
                  ? 'שלום! אני כאן כדי להוביל אותך במסע של גילוי עצמי וצמיחה אישית. מה תרצה לחקור היום?'
                  : 'Hello! I\'m here to guide you on a journey of self-discovery and personal growth. What would you like to explore today?'}
              </p>
            </motion.div>
          ) : (
                  <AnimatePresence>
                    {messages.map((message, index) => (
                      <motion.div
                        key={message.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        transition={{ delay: index * 0.05 }}
                        className="mb-6"
                      >
                        <MessageBubble message={message} />
                      </motion.div>
                    ))}
                    {loading && (
                      <motion.div
                        key="loading-dots"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        transition={{ duration: 0.2 }}
                        className="flex justify-end mb-6"
                      >
                  <div className="bg-white/80 backdrop-blur-sm rounded-2xl px-6 py-4 shadow-glass border border-accent/20">
                    <div className="flex space-x-2 rtl:space-x-reverse">
                      <motion.div
                        className="w-2 h-2 bg-accent rounded-full"
                        animate={{ y: [0, -10, 0] }}
                        transition={{ repeat: Infinity, duration: 0.6, delay: 0 }}
                      />
                      <motion.div
                        className="w-2 h-2 bg-accent rounded-full"
                        animate={{ y: [0, -10, 0] }}
                        transition={{ repeat: Infinity, duration: 0.6, delay: 0.2 }}
                      />
                      <motion.div
                        className="w-2 h-2 bg-accent rounded-full"
                        animate={{ y: [0, -10, 0] }}
                        transition={{ repeat: Infinity, duration: 0.6, delay: 0.4 }}
                      />
                    </div>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </AnimatePresence>
          )}
        </div>
      </div>

      {/* Input Area / Voice Control Bar */}
      <AnimatePresence mode="wait">
        {isVoiceMode ? (
          <VoiceControlBar
            key="voice-bar"
            language={i18n.language as 'he' | 'en'}
            voiceGender={voiceGender}
            onVoiceGenderChange={setVoiceGender}
            onMessageSync={handleVoiceMessage}
            onAIResponseReady={(speakFn) => {
              speakFunctionRef.current = speakFn;
            }}
            onStopSessionReady={(stopFn) => {
              stopVoiceSessionRef.current = stopFn;
            }}
            onStop={() => setIsVoiceMode(false)}
          />
        ) : (
          <div key="text-input" className="px-2 pb-6">
            <div className="w-full">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className="bg-white/90 backdrop-blur-md shadow-glass rounded-2xl border border-gray-200/50 p-4"
              >
                <form onSubmit={handleSubmit} className="flex items-end gap-3">
                  {/* Text Input */}
                  <textarea
                    ref={inputRef}
                    value={inputValue}
                    onChange={(e) => {
                      if (!chatLockedByForm) setInputValue(e.target.value);
                    }}
                    onKeyDown={handleKeyDown}
                    placeholder={chatLockedByForm ? t('chat.formBlocksTyping') : t('chat.placeholder')}
                    disabled={loading || chatLockedByForm}
                    className="
                      flex-1 resize-none rounded-xl border-0 bg-transparent
                      px-4 py-3 text-gray-900 placeholder-gray-500
                      focus:outline-none focus:ring-2 focus:ring-accent/30
                      disabled:opacity-50 max-h-32 font-medium
                    "
                    rows={1}
                    style={{ minHeight: '48px' }}
                  />

                  {/* Voice Mode Button */}
                  <motion.button
                    type="button"
                    whileHover={chatLockedByForm ? undefined : { scale: 1.05 }}
                    whileTap={chatLockedByForm ? undefined : { scale: 0.95 }}
                    onClick={() => {
                      if (chatLockedByForm) return;
                      if (isVoiceMode) {
                        // Stop voice session FIRST before changing mode
                        console.log('🎤 Mic button clicked - stopping voice mode');
                        if (stopVoiceSessionRef.current) {
                          stopVoiceSessionRef.current();
                        }
                        // Small delay to ensure stop completes
                        setTimeout(() => {
                          setIsVoiceMode(false);
                        }, 100);
                      } else {
                        console.log('🎤 Mic button clicked - starting voice mode');
                        setIsVoiceMode(true);
                      }
                    }}
                    disabled={chatLockedByForm}
                    className={`
                      flex-shrink-0 p-3 rounded-xl transition-all
                      ${chatLockedByForm ? 'opacity-40 cursor-not-allowed' : ''}
                      ${isVoiceMode
                        ? 'bg-red-500 text-white shadow-glow animate-pulse'
                        : 'bg-gradient-to-br from-purple-500 to-purple-700 text-white hover:shadow-glow'
                      }
                    `}
                    title={
                      chatLockedByForm
                        ? t('chat.formBlocksTyping')
                        : i18n.language === 'he'
                          ? 'מצב קולי'
                          : 'Voice Mode'
                    }
                  >
                    <Mic size={20} />
                  </motion.button>

                  {/* Send Button */}
                  <motion.button
                    type="submit"
                    disabled={chatLockedByForm || !inputValue.trim() || loading}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="
                      flex-shrink-0 p-3 rounded-xl
                      bg-gradient-to-br from-accent to-accent-dark text-white
                      hover:shadow-glow transition-all
                      disabled:opacity-50 disabled:cursor-not-allowed
                      disabled:hover:shadow-none
                    "
                    title={t('chat.send')}
                  >
                    <Send size={20} />
                  </motion.button>
                </form>
              </motion.div>
            </div>
          </div>
        )}
      </AnimatePresence>
      </div>

      {/* RIGHT: Conversation History Sidebar */}
      <Sidebar
        conversations={conversations}
        activeId={conversationId}
        onSelect={handleSelectConversation}
        onNewChat={handleNewChat}
        onDelete={handleDeleteConversation}
        onShare={handleShareConversation}
        isRTL={i18n.dir() === 'rtl'}
      />
    </div>
  );
};
