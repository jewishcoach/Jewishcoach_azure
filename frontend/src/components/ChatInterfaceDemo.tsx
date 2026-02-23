import { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Send, Sparkles, Mic } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChat } from '../hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { PhaseIndicator } from './PhaseIndicator';
import { Sidebar } from './Sidebar';
import { VoiceControlBar } from './VoiceControlBar';
import { InsightHub } from './InsightHub/InsightHub';
import { apiClient } from '../services/api';
import type { Conversation, ToolCall } from '../types';
import type { VoiceGender } from '../constants/voices';

// HARDCODED NGROK URL FOR DEMO MODE
const DEMO_API_URL = 'https://poorly-molecular-louie.ngrok-free.dev/api';
const DEMO_FRONTEND_URL = 'https://74ba09cc388888.lhr.life';

interface ChatInterfaceDemoProps {
  displayName?: string | null;
}

/**
 * Demo Mode version of ChatInterface - doesn't use Clerk authentication
 * Used when running on tunnel domains (.lhr.life, .ngrok-free.app)
 */
export const ChatInterfaceDemo = ({ displayName }: ChatInterfaceDemoProps) => {
  const { t, i18n } = useTranslation();
  const [inputValue, setInputValue] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [voiceGender, setVoiceGender] = useState<VoiceGender>('female');
  const { messages, loading, currentPhase, conversationId, activeTool, sendMessage, loadConversation, startNewConversation } = useChat(displayName);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const speakFunctionRef = useRef<((text: string) => Promise<void>) | null>(null);
  const stopVoiceSessionRef = useRef<(() => void) | null>(null);
  const isSendingRef = useRef(false);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Initialize: Set demo token and fetch conversations
  useEffect(() => {
    const init = async () => {
      try {
        console.log('🔧 [DEMO] Forcing API URL to:', DEMO_API_URL);
        
        // Override the baseURL (access private property)
        (apiClient as any).client.defaults.baseURL = DEMO_API_URL;
        apiClient.setToken('demo_tunnel_token');
        
        console.log('🔧 [DEMO] Current baseURL:', (apiClient as any).client.defaults.baseURL);
        
        const convs = await apiClient.getConversations();
        setConversations(convs);
      } catch (error) {
        console.error('❌ [DEMO] Error initializing:', error);
      }
    };
    init();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputValue.trim() || loading || isSendingRef.current) {
      console.log('⚠️ [DEMO] Ignoring submit - empty or already sending');
      return;
    }

    const messageToSend = inputValue.trim();
    setInputValue('');
    isSendingRef.current = true;
    
    // Force override API URL again before sending (to be safe)
    (apiClient as any).client.defaults.baseURL = DEMO_API_URL;
    
    console.log('📤 [DEMO] Sending message:', messageToSend);
    console.log('📤 [DEMO] Current baseURL:', (apiClient as any).client.defaults.baseURL);
    console.log('📤 [DEMO] Stream URL:', apiClient.getMessageStreamUrl(conversationId || 0));
    
    try {
      await sendMessage(messageToSend, i18n.language, 'demo_tunnel_token');
      
      console.log('✅ [DEMO] Message sent successfully');
      
      // Refresh conversations
      const convs = await apiClient.getConversations();
      setConversations(convs);
    } catch (error) {
      console.error('❌ [DEMO] Error sending message:', error);
    } finally {
      setTimeout(() => {
        isSendingRef.current = false;
      }, 300);
    }
  };

  const handleSelectConversation = async (id: number) => {
    if (isVoiceMode && stopVoiceSessionRef.current) {
      stopVoiceSessionRef.current();
      setIsVoiceMode(false);
    }
    await loadConversation(id);
  };

  const handleNewChat = async () => {
    if (isVoiceMode && stopVoiceSessionRef.current) {
      stopVoiceSessionRef.current();
      setIsVoiceMode(false);
    }
    await startNewConversation();
    const convs = await apiClient.getConversations();
    setConversations(convs);
  };

  const handleDeleteConversation = async (id: number) => {
    try {
      await apiClient.deleteConversation(id);
      const convs = await apiClient.getConversations();
      setConversations(convs);
      
      if (conversationId === id) {
        await handleNewChat();
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  return (
    <div className="flex h-full w-full overflow-hidden">
      <Sidebar 
        conversations={conversations}
        activeId={conversationId}
        onSelect={(id) => handleSelectConversation(id)}
        onNewChat={handleNewChat}
        onDelete={handleDeleteConversation}
        onShare={() => {}}
        isRTL={i18n.language === 'he'}
      />
      
      <div className="flex-1 flex flex-col min-w-0 relative">
        <PhaseIndicator currentPhase={currentPhase} language={i18n.language} />
        
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
          <AnimatePresence mode="popLayout">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </AnimatePresence>
          
          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 text-white/60"
            >
              <div className="flex gap-1">
                <motion.span
                  animate={{ y: [0, -10, 0] }}
                  transition={{ repeat: Infinity, duration: 0.6, delay: 0 }}
                  className="w-2 h-2 bg-white/60 rounded-full"
                />
                <motion.span
                  animate={{ y: [0, -10, 0] }}
                  transition={{ repeat: Infinity, duration: 0.6, delay: 0.1 }}
                  className="w-2 h-2 bg-white/60 rounded-full"
                />
                <motion.span
                  animate={{ y: [0, -10, 0] }}
                  transition={{ repeat: Infinity, duration: 0.6, delay: 0.2 }}
                  className="w-2 h-2 bg-white/60 rounded-full"
                />
              </div>
              <span className="text-sm">{t('thinking')}</span>
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {isVoiceMode && (
          <VoiceControlBar 
            language={i18n.language as 'he' | 'en'}
            voiceGender={voiceGender}
            onVoiceGenderChange={setVoiceGender}
            onMessageSync={async () => {}}
            onAIResponseReady={(fn) => { speakFunctionRef.current = fn; }}
            onStopSessionReady={(fn) => { stopVoiceSessionRef.current = fn; }}
            onStop={() => {
              if (stopVoiceSessionRef.current) stopVoiceSessionRef.current();
              setIsVoiceMode(false);
            }}
          />
        )}

        <form onSubmit={handleSubmit} className="border-t border-white/10 p-4 bg-primary/50 backdrop-blur-sm">
          <div className="flex gap-3 items-end">
            <button
              type="button"
              disabled
              className="px-4 py-3 rounded-xl bg-white/5 text-white/30 transition-colors cursor-not-allowed flex items-center gap-2"
              title={t('voiceModeDisabledInDemo')}
            >
              <Mic className="w-5 h-5" />
            </button>
            
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                placeholder={t('chatPlaceholder')}
                disabled={loading || isVoiceMode}
                className="w-full px-4 py-3 bg-white/10 text-white placeholder-white/40 rounded-xl border border-white/10 focus:border-accent focus:outline-none resize-none min-h-[48px] max-h-32"
                rows={1}
                style={{
                  direction: i18n.language === 'he' ? 'rtl' : 'ltr',
                }}
              />
            </div>
            
            <button
              type="submit"
              disabled={!inputValue.trim() || loading || isVoiceMode}
              className="px-6 py-3 rounded-xl bg-accent hover:bg-accent-dark disabled:bg-white/5 disabled:text-white/30 text-white transition-colors flex items-center gap-2"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>
      </div>

      {conversationId && (
        <InsightHub 
          conversationId={conversationId}
          currentPhase={currentPhase}
          activeTool={activeTool}
          onToolSubmit={async () => {}}
        />
      )}
    </div>
  );
};

