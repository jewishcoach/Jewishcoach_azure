import { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Send, Mic } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@clerk/clerk-react';
import { useChat } from '../../hooks/useChat';
import { VisionLadder } from './VisionLadder';
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
  const onArchiveClick = useCallback(() => setArchiveOpen(true), []);

  // Dashboard: full-screen only. No HudPanel, no Vision Ladder.
  if (showDashboard) {
    return (
      <>
        <div className="flex-1 flex overflow-hidden bg-[#F0F1F3]">
          <div className="flex-1 min-w-0 overflow-hidden">
            <Dashboard onBack={onCloseDashboard} />
          </div>
        </div>
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
      </>
    );
  }

  return (
    <div
      className="flex flex-col md:flex-row h-full w-full bg-[#020617] overflow-y-auto md:overflow-hidden"
      dir={i18n.dir()}
    >
      {/* RIGHT in RTL: Cognitive HUD - Mekor, Teva, Archive, Videos. On mobile: below chat */}
      <div className="order-2 md:order-1 w-full md:w-64 lg:w-72 flex-shrink-0 border-t md:border-t-0 md:border-r border-white/[0.08] bg-[#1e293b] overflow-hidden min-h-0 max-h-[45vh] md:max-h-none">
        <HudPanel conversationId={conversationId} currentPhase={currentPhase} onArchiveClick={() => setArchiveOpen(true)} />
      </div>

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

      {/* CENTER: Chat area - cream background. On mobile: first */}
      <div className="order-1 md:order-2 flex flex-col min-w-0 relative overflow-hidden bg-[#F5F5F0] flex-1">
        <ShehiyaProgress loading={loading} />

        <div className="flex-1 overflow-y-auto px-10 py-10 custom-scrollbar bg-[#F5F5F0]">
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-full text-center py-24 px-10"
            >
              <p className="text-[#2E3A56]/90 text-[16px] max-w-md" style={{ fontFamily: 'Inter, sans-serif', fontWeight: 300, lineHeight: 1.6 }}>
                {i18n.language === 'he'
                  ? 'שלום! על מה תרצה להתאמן היום?'
                  : 'Hello! What would you like to work on today?'}
              </p>
            </motion.div>
          ) : (
            <div className="space-y-9">
              <AnimatePresence>
                {messages.map((message) => (
                  <WorkspaceMessageBubble key={message.id} message={message} />
                ))}
              </AnimatePresence>
              {loading && (
                <div className="flex justify-start">
                  <div
                    className="rounded-xl px-6 py-4 flex items-center gap-3 bg-white/80 border border-[#E2E4E8] shadow-sm"
                  >
                    <div className="flex gap-1">
                      <span className="w-2 h-2 rounded-full bg-[#B38728] animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 rounded-full bg-[#B38728] animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 rounded-full bg-[#B38728] animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-[14px] font-light text-[#2E3A56]/80" style={{ fontFamily: 'Inter, sans-serif' }}>
                      {i18n.language === 'he' ? 'המאמן חושב...' : 'Coach is thinking...'}
                    </span>
                  </div>
                </div>
              )}
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
            <div key="text-input" className="p-9 border-t border-[#E2E4E8] bg-[#F5F5F0]">
              <form onSubmit={handleSubmit} className="flex items-end gap-5">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={t('chat.placeholder')}
                  disabled={loading}
                  className="flex-1 resize-none rounded-xl px-6 py-5 text-[16px] max-h-28 placeholder-[#5A6B8A]/60 focus:border-[#B38728]/50 focus:ring-2 focus:ring-[#B38728]/20 focus:outline-none"
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontWeight: 300,
                    lineHeight: 1.6,
                    minHeight: '48px',
                    background: '#FFFFFF',
                    border: '1px solid #E2E4E8',
                    color: '#2E3A56',
                  }}
                  rows={1}
                />
                <button
                  type="button"
                  onClick={() => setIsVoiceMode(true)}
                  className="p-4 rounded-xl bg-white border border-[#E2E4E8] hover:bg-[#F0F1F3] text-[#2E3A56]/80 transition-colors shadow-sm"
                >
                  <Mic size={18} strokeWidth={1.5} />
                </button>
                <button
                  type="submit"
                  disabled={!inputValue.trim() || loading}
                  className="p-4 rounded-xl text-[#020617] font-light disabled:opacity-50 transition-all"
                  style={{
                    background: 'linear-gradient(45deg, #BF953F, #FCF6BA, #B38728, #FBF5B7, #AA771C)',
                    filter: 'drop-shadow(0 0 5px rgba(212, 175, 55, 0.5))',
                  }}
                >
                  <Send size={18} strokeWidth={1.5} />
                </button>
              </form>
            </div>
          )}
        </AnimatePresence>
      </div>

      {/* LEFT in RTL: Vision Ladder. On mobile: last (scroll to see) */}
      <div className="order-3 w-[280px] min-w-[280px] flex-shrink-0 h-full min-h-[400px] border-t md:border-t-0 md:border-l border-white/[0.08] bg-[#1e293b] overflow-hidden">
        <VisionLadder currentStep={currentPhase} />
      </div>
    </div>
  );
};
