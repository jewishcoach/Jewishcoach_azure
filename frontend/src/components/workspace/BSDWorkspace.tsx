import { useState, useRef, useEffect, useCallback } from 'react';
import { PHASE_TO_STAGES } from './phaseMapping';
import { useTranslation } from 'react-i18next';
import { Send, Mic, Square } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@clerk/clerk-react';
import { useChat } from '../../hooks/useChat';
import { useVoiceRecord } from '../../hooks/useVoiceRecord';
import { VisionLadder } from './VisionLadder';
import { ArchiveDrawer } from './ArchiveDrawer';
import { HudPanel } from './HudPanel';
import { ShehiyaProgress } from './ShehiyaProgress';
import { WorkspaceMessageBubble } from './WorkspaceMessageBubble';
import { ActiveToolRenderer } from '../InsightHub/ActiveToolRenderer';
import { Dashboard } from '../Dashboard';
import { QuotaExceededModal } from '../QuotaExceededModal';
import { apiClient } from '../../services/api';
import type { Conversation } from '../../types';
import { WORKSPACE_CHAT_FONT } from '../../constants/workspaceFonts';

interface BSDWorkspaceProps {
  displayName?: string | null;
  showDashboard?: boolean;
  onCloseDashboard?: () => void;
  onShowBilling?: () => void;
  archiveOpen?: boolean;
  onArchiveOpenChange?: (open: boolean) => void;
  /** Incremented from App header (mobile) — starts a new conversation */
  headerNewChatTick?: number;
}

export const BSDWorkspace = ({
  displayName,
  showDashboard = false,
  onCloseDashboard,
  onShowBilling,
  archiveOpen: archiveOpenProp,
  onArchiveOpenChange,
  headerNewChatTick = 0,
}: BSDWorkspaceProps) => {
  const { t, i18n } = useTranslation();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [inputValue, setInputValue] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [archiveOpenLocal, setArchiveOpenLocal] = useState(false);
  const archiveOpen = archiveOpenProp ?? archiveOpenLocal;
  const setArchiveOpen = onArchiveOpenChange ?? setArchiveOpenLocal;
  const { messages, loading, currentPhase, conversationId, activeTool, quotaExceeded, dismissQuotaModal, sendMessage, loadConversation, startNewConversation, applyToolResponse } = useChat(displayName);
  const { isRecording, livePreview, startRecording, stopRecording } = useVoiceRecord(i18n.language, getToken);
  const [recordingInputBase, setRecordingInputBase] = useState<string | null>(null);

  useEffect(() => {
    if (!isRecording) setRecordingInputBase(null);
  }, [isRecording]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatToolRef = useRef<HTMLDivElement>(null);
  const messagesScrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isSendingRef = useRef(false);

  const handlePhaseClick = useCallback((phaseIndex: number) => {
    const stages = PHASE_TO_STAGES[phaseIndex];
    if (!stages || stages.length === 0) return;
    const container = messagesScrollRef.current;
    if (!container) return;
    const selector = stages.map(s => `[data-phase="${s}"]`).join(',');
    const firstMatch = container.querySelector(selector) as HTMLElement | null;
    if (firstMatch) {
      firstMatch.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      // שלב טרם הושג – גלילה לסוף השיחה
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!activeTool) return;
    const t = window.setTimeout(() => {
      chatToolRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 120);
    return () => window.clearTimeout(t);
  }, [activeTool]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;

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
  }, [isLoaded, isSignedIn, getToken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || loading || isSendingRef.current) return;
    const messageToSend = inputValue.trim();
    setInputValue('');
    isSendingRef.current = true;
    try {
      await sendMessage(messageToSend, i18n.language, async () => (await getToken()) || apiClient.getToken() || null);
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
    await loadConversation(id);
  };

  const handleNewChat = async () => {
    await startNewConversation();
  };

  const lastHeaderNewChatTick = useRef(headerNewChatTick);
  useEffect(() => {
    if (headerNewChatTick <= 0) return;
    if (headerNewChatTick === lastHeaderNewChatTick.current) return;
    lastHeaderNewChatTick.current = headerNewChatTick;
    void startNewConversation();
  }, [headerNewChatTick, startNewConversation]);

  const handleMicClick = useCallback(async () => {
    if (isRecording) {
      const transcript = await stopRecording();
      if (transcript.trim()) {
        setInputValue((prev) => (prev ? `${prev} ${transcript}` : transcript));
        inputRef.current?.focus();
      }
    } else {
      const base = inputValue;
      const ok = await startRecording();
      if (ok) setRecordingInputBase(base);
    }
  }, [isRecording, inputValue, startRecording, stopRecording]);

  const handleToolSubmit = async (submission: { tool_type: string; data: any }): Promise<void> => {
    if (!conversationId) return;
    try {
      const token = await getToken();
      if (!token) return;
      apiClient.setToken(token);
      const result = await apiClient.submitToolResponse(conversationId, submission.tool_type, submission.data);
      applyToolResponse(result);
      const convs = await apiClient.getConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Error submitting tool:', error);
    }
  };

  const handleDeleteConversation = async (id: number) => {
    const confirmMessage = t('chat.deleteConfirm');
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
      const lines = [(conv.title || t('chat.conversation')), ...(conv.messages || []).map((m: any) => `${m.role === 'assistant' ? t('chat.coach') : t('chat.me')}: ${m.content}`)];
      await navigator.clipboard.writeText(lines.join('\n'));
      window.alert(t('chat.copied'));
    } catch (error) {
      console.error('Error sharing:', error);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      e.currentTarget.form?.requestSubmit();
    }
  };

  const displayValue =
    recordingInputBase !== null && isRecording
      ? `${recordingInputBase}${livePreview ? ' ' + livePreview : ''}`
      : inputValue;

  const isRTL = i18n.dir() === 'rtl';
  const onArchiveClick = useCallback(() => setArchiveOpen(true), []);

  // Dashboard: full-screen only. No HudPanel, no Vision Ladder.
  if (showDashboard) {
    return (
      <>
        <div className="flex-1 flex overflow-hidden bg-[#F0F1F3] min-h-0">
          <div className="flex-1 min-w-0 min-h-0 overflow-hidden flex flex-col">
            <Dashboard onBack={onCloseDashboard} onShowBilling={onShowBilling} />
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
    <>
      <QuotaExceededModal
        isOpen={quotaExceeded}
        onClose={dismissQuotaModal}
        onGoToSubscription={() => {
          dismissQuotaModal();
          onShowBilling?.();
        }}
      />
    <div
      className="flex flex-col md:flex-row h-full w-full bg-[#020617] overflow-hidden"
      dir={i18n.dir()}
    >
      {/* Mobile: [Stages strip | Chat] row, then HUD below. Desktop: HUD | Chat | Ladder */}
      <div className="flex flex-1 min-h-0 flex-col md:flex-row w-full">
        {/* HUD - desktop only; mobile uses stages strip insights */}
        <div className="hidden md:flex order-3 md:order-1 w-64 lg:w-72 flex-shrink-0 border-r border-white/[0.08] bg-[#1e293b] overflow-hidden min-h-0 flex flex-col">
          <HudPanel
            conversationId={conversationId}
            currentPhase={currentPhase}
            loading={loading}
            onArchiveClick={() => setArchiveOpen(true)}
            onNewChat={() => void handleNewChat()}
          />
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

        {/* Chat area: mobile [strip|messages] + input below; desktop messages + input */}
        <div className="order-1 md:order-2 flex flex-1 min-w-0 min-h-0 flex-col">
          {/* Messages row: mobile has strip alongside; desktop messages only */}
          <div className="flex flex-1 min-w-0 min-h-0 flex-row">
            {/* Mobile: stages strip - height only up to messages, not input */}
            <div className="md:hidden flex-shrink-0 self-stretch min-h-0">
              <VisionLadder currentStep={currentPhase} onPhaseClick={handlePhaseClick} compact conversationId={conversationId} />
            </div>
            <div className="flex flex-col min-w-0 flex-1 relative overflow-hidden bg-[#F5F5F0]">
              <ShehiyaProgress loading={loading} />
              {/* dir=ltr כאן קובע יישור פיזי: מאמן מימין, משתמש משמאל (גם בעברית). כיוון טקסט בבועות — ב-WorkspaceMessageBubble */}
              <div
                ref={messagesScrollRef}
                className="flex-1 overflow-y-auto px-3 py-4 md:px-10 md:py-10 custom-scrollbar bg-[#F5F5F0]"
                dir="ltr"
              >
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-full text-center py-16 md:py-24 px-4 md:px-10"
              dir={i18n.dir()}
            >
              <p className="text-[#2E3A56]/90 text-[14px] md:text-[16px] max-w-md" style={{ fontFamily: WORKSPACE_CHAT_FONT, fontWeight: 400, lineHeight: 1.6 }}>
                {t('chat.emptyHint')}
              </p>
            </motion.div>
          ) : (
            <div className="space-y-5 md:space-y-9">
              <AnimatePresence>
                {messages.map((message, idx) => {
                  const phase = message.role === 'assistant' && message.meta?.phase
                    ? message.meta.phase
                    : messages.slice(0, idx).reverse().find(m => m.role === 'assistant' && m.meta?.phase)?.meta?.phase ?? 'S0';
                  return (
                    <div key={message.id} data-phase={phase} data-message-id={message.id}>
                      {/* No word-by-word typing: partial Hebrew breaks RTL/BiDi until the full string is shown */}
                      <WorkspaceMessageBubble
                        message={message}
                        animateTyping={false}
                        dir={i18n.dir() as 'ltr' | 'rtl'}
                      />
                    </div>
                  );
                })}
              </AnimatePresence>
              {activeTool && (
                <div ref={chatToolRef} className="flex justify-end">
                  <div
                    className="w-full max-w-[90%] md:max-w-[85%] rounded-xl px-5 py-4 md:px-9 md:py-6 shadow-sm bg-white border border-[#E2E4E8]"
                    dir={i18n.dir()}
                  >
                    <ActiveToolRenderer
                      tool={activeTool}
                      onSubmit={handleToolSubmit}
                      language={i18n.language as 'he' | 'en'}
                    />
                  </div>
                </div>
              )}
              {loading && (
                <div className="flex justify-end">
                  <div
                    className="rounded-xl px-6 py-4 flex items-center gap-3 bg-white shadow-md border border-[#E2E4E8]"
                  >
                    <div className="flex gap-1">
                      <span className="w-2.5 h-2.5 rounded-full bg-[#AA771C] animate-bounce shadow-sm" style={{ animationDelay: '0ms' }} />
                      <span className="w-2.5 h-2.5 rounded-full bg-[#AA771C] animate-bounce shadow-sm" style={{ animationDelay: '150ms' }} />
                      <span className="w-2.5 h-2.5 rounded-full bg-[#AA771C] animate-bounce shadow-sm" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span
                      className="text-[14px] font-medium text-[#2E3A56]/80"
                      style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                      dir={i18n.dir()}
                    >
                      {t('chat.thinkingCoach')}
                    </span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
              </div>
            </div>
          </div>

          {/* Input - below messages; full width on mobile */}
          <div className="p-4 md:p-9 border-t border-[#E2E4E8] bg-[#F5F5F0] flex-shrink-0">
              <form onSubmit={handleSubmit} className="flex items-end gap-3 md:gap-5">
                <textarea
                  ref={inputRef}
                  value={displayValue}
                  onChange={(e) => {
                    if (!isRecording) setInputValue(e.target.value);
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder={t('chat.placeholder')}
                  disabled={loading || isRecording}
                  className="flex-1 min-w-0 resize-none rounded-xl px-4 md:px-6 py-3 md:py-5 text-[14px] md:text-[16px] max-h-28 placeholder-[#5A6B8A]/60 placeholder:text-[12px] md:placeholder:text-[16px] focus:border-[#B38728]/50 focus:ring-2 focus:ring-[#B38728]/20 focus:outline-none"
                  style={{
                    fontFamily: WORKSPACE_CHAT_FONT,
                    fontWeight: 400,
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
                  onClick={handleMicClick}
                  disabled={loading}
                  title={isRecording ? t('chat.stopRecording') : t('chat.recordVoice')}
                  className={`p-3 md:p-4 rounded-xl border transition-colors shadow-sm min-h-[44px] min-w-[44px] flex items-center justify-center ${
                    isRecording
                      ? 'bg-[#2E3A56]/15 border-[#2E3A56]/40 text-[#2E3A56] hover:bg-[#2E3A56]/25'
                      : 'bg-white border-[#E2E4E8] hover:bg-[#F0F1F3] text-[#2E3A56]/80'
                  }`}
                >
                  {isRecording ? <Square size={18} strokeWidth={2} fill="currentColor" /> : <Mic size={18} strokeWidth={1.5} />}
                </button>
                <button
                  type="submit"
                  disabled={!displayValue.trim() || loading || isRecording}
                  className="premium-cta-btn p-3 md:p-4 rounded-xl text-[#2E3A56] font-semibold disabled:opacity-50 min-h-[44px] min-w-[44px] flex items-center justify-center flex-shrink-0"
                >
                  <Send size={18} strokeWidth={1.5} />
                </button>
            </form>
          </div>
        </div>

        {/* Desktop: Vision Ladder full */}
        <div className="hidden md:flex order-3 w-[280px] min-w-[280px] flex-shrink-0 h-full min-h-[400px] border-l border-white/[0.08] bg-[#1e293b] overflow-hidden">
          <VisionLadder currentStep={currentPhase} onPhaseClick={handlePhaseClick} />
        </div>
      </div>
    </div>
    </>
  );
};
