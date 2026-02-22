import { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Send, Mic } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@clerk/clerk-react';
import { useChat } from '../../hooks/useChat';
import { BsdScale } from './BsdScale';
import { ArchiveDrawer } from './ArchiveDrawer';
import { HudPanel } from './HudPanel';
import { ShehiyaProgress } from './ShehiyaProgress';
import { WorkspaceMessageBubble } from './WorkspaceMessageBubble';
import { VoiceControlBar } from '../VoiceControlBar';
import { Dashboard } from '../Dashboard';
import { apiClient } from '../../services/api';
import type { Conversation, ToolCall } from '../../types';
import type { VoiceGender } from '../../constants/voices';

interface BSDWorkspaceProps {
  displayName?: string | null;
  showDashboard?: boolean;
  onCloseDashboard?: () => void;
}

export const BSDWorkspace = ({ displayName, showDashboard = false, onCloseDashboard }: BSDWorkspaceProps) => {
  const { t, i18n } = useTranslation();
  const { getToken } = useAuth();
  const [inputValue, setInputValue] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [voiceGender, setVoiceGender] = useState<VoiceGender>('female');
  const { messages, loading, currentPhase, conversationId, activeTool, sendMessage, loadConversation, startNewConversation } = useChat(displayName);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const speakFunctionRef = useRef<((text: string) => Promise<void>) | null>(null);
  const stopVoiceSessionRef = useRef<(() => void) | null>(null);
  const isSendingRef = useRef(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const init = async () => {
      try {
        const token = (await getToken()) || apiClient.getToken();
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
  }, [getToken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || loading || isSendingRef.current) return;
    const messageToSend = inputValue.trim();
    setInputValue('');
    isSendingRef.current = true;
    try {
      const token = (await getToken()) || apiClient.getToken();
      if (!token) return;
      await sendMessage(messageToSend, i18n.language, token);
      const convs = await apiClient.getConversations();
      setConversations(convs);
      inputRef.current?.focus();
    } catch (error) {
      console.error('Error sending message:', error);
      inputRef.current?.focus();
    } finally {
      setTimeout(() => { isSendingRef.current = false; }, 300);
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
  };

  const handleDeleteConversation = async (id: number) => {
    const confirmMessage = i18n.language === 'he' ? 'למחוק את השיחה הזו?' : 'Delete this conversation?';
    if (!window.confirm(confirmMessage)) return;
    try {
      const token = await getToken();
      if (!token) return;
      apiClient.setToken(token);
      await apiClient.deleteConversation(id);
      const convs = await apiClient.getConversations();
      setConversations(convs);
      if (conversationId === id) await startNewConversation();
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
      const lines = [(conv.title || 'שיחה'), ...(conv.messages || []).map((m: any) => `${m.role === 'assistant' ? 'מאמן' : 'אני'}: ${m.content}`)];
      await navigator.clipboard.writeText(lines.join('\n'));
      window.alert(i18n.language === 'he' ? 'הועתק ללוח' : 'Copied to clipboard');
    } catch (error) {
      console.error('Error sharing:', error);
    }
  };

  const handleVoiceMessage = useCallback(async (role: 'user' | 'assistant', content: string) => {
    if (role !== 'user' || isSendingRef.current) return;
    const token = await getToken();
    if (!token) return;
    isSendingRef.current = true;
    try {
      await sendMessage(content, i18n.language, token, (responseText) => {
        if (speakFunctionRef.current) speakFunctionRef.current(responseText);
      });
    } catch (error) {
      console.error('Error in voice message:', error);
    } finally {
      setTimeout(() => { isSendingRef.current = false; }, 300);
    }
  }, [getToken, i18n.language, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      e.currentTarget.form?.requestSubmit();
    }
  };

  const isRTL = i18n.dir() === 'rtl';

  return (
    <div className="flex h-full w-full bg-[#0F172A]">
      {/* LEFT: BSD Scale */}
      <BsdScale currentStep={currentPhase} onArchiveClick={() => setArchiveOpen(true)} />

      {/* Archive Drawer */}
      <ArchiveDrawer
        isOpen={archiveOpen}
        onClose={() => setArchiveOpen(false)}
        conversations={conversations}
        activeId={conversationId}
        onSelect={handleSelectConversation}
        onNewChat={handleNewChat}
        onDelete={handleDeleteConversation}
        onShare={handleShareConversation}
        isRTL={isRTL}
      />

      {/* CENTER: Chat - shrinks when Dashboard opens */}
      <motion.div
        className="flex flex-col min-w-0 relative overflow-hidden"
        initial={false}
        animate={{ flex: showDashboard ? 0 : 1, minWidth: showDashboard ? 0 : undefined }}
        transition={{ type: 'tween', duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
      >
        <ShehiyaProgress loading={loading} />

        <div className="flex-1 overflow-y-auto px-6 py-6 custom-scrollbar">
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-full text-center py-20"
            >
              <p className="text-white/60 text-sm max-w-md">
                {i18n.language === 'he'
                  ? 'שלום! על מה תרצה להתאמן היום?'
                  : 'Hello! What would you like to work on today?'}
              </p>
            </motion.div>
          ) : (
            <div className="space-y-4">
              <AnimatePresence>
                {messages.map((message) => (
                  <WorkspaceMessageBubble key={message.id} message={message} />
                ))}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <AnimatePresence mode="wait">
          {isVoiceMode ? (
            <VoiceControlBar
              key="voice-bar"
              language={i18n.language as 'he' | 'en'}
              voiceGender={voiceGender}
              onVoiceGenderChange={setVoiceGender}
              onMessageSync={handleVoiceMessage}
              onAIResponseReady={(fn) => { speakFunctionRef.current = fn; }}
              onStopSessionReady={(fn) => { stopVoiceSessionRef.current = fn; }}
              onStop={() => setIsVoiceMode(false)}
            />
          ) : (
            <div key="text-input" className="p-4 border-t border-white/10">
              <form onSubmit={handleSubmit} className="flex items-end gap-3">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={t('chat.placeholder')}
                  disabled={loading}
                  className="flex-1 resize-none rounded-[4px] bg-white/5 border border-white/10 px-4 py-3 text-white placeholder-white/40 focus:outline-none focus:border-amber-500/50 text-sm max-h-28"
                  rows={1}
                  style={{ minHeight: '44px' }}
                />
                <button
                  type="button"
                  onClick={() => setIsVoiceMode(true)}
                  className="p-3 rounded-[4px] bg-white/10 hover:bg-white/15 text-white transition-colors"
                >
                  <Mic size={18} />
                </button>
                <button
                  type="submit"
                  disabled={!inputValue.trim() || loading}
                  className="p-3 rounded-[4px] bg-amber-500/80 hover:bg-amber-500 text-white disabled:opacity-50 transition-colors"
                >
                  <Send size={18} />
                </button>
              </form>
            </div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* RIGHT: HUD / Dashboard - expands to center when Dashboard opens */}
      <motion.div
        className="flex flex-col border-l border-white/10 bg-[#0F172A]/80 overflow-hidden flex-shrink-0"
        initial={false}
        animate={{
          flex: showDashboard ? 1 : 0,
          minWidth: showDashboard ? 0 : 256,
          width: showDashboard ? 'auto' : 256,
        }}
        transition={{ type: 'tween', duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
      >
        <AnimatePresence mode="wait">
          {showDashboard ? (
            <motion.div
              key="dashboard"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="flex-1 min-w-0 overflow-auto"
            >
              <Dashboard onBack={onCloseDashboard} />
            </motion.div>
          ) : (
            <motion.div
              key="hud"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="w-64 flex-shrink-0 h-full"
            >
              <HudPanel conversationId={conversationId} />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};
