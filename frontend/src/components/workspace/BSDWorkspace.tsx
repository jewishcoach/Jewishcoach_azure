import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { PHASE_TO_STAGES } from './phaseMapping';
import { useTranslation } from 'react-i18next';
import { Loader2, Send, Mic, Square } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@clerk/clerk-react';
import { useChat } from '../../hooks/useChat';
import { useChatScrollIntoLatest } from '../../hooks/useChatScrollIntoLatest';
import { useVoiceRecord } from '../../hooks/useVoiceRecord';
import { VisionLadder } from './VisionLadder';
import { ArchiveDrawer } from './ArchiveDrawer';
import { HudPanel } from './HudPanel';
import { ShehiyaProgress } from './ShehiyaProgress';
import { WorkspaceMessageBubble } from './WorkspaceMessageBubble';
import { StationCheckpointBar } from './StationCheckpointBar';
import { ActiveToolRenderer } from '../InsightHub/ActiveToolRenderer';
import { Dashboard } from '../Dashboard';
import { QuotaExceededModal } from '../QuotaExceededModal';
import { apiClient } from '../../services/api';
import type { Conversation } from '../../types';
import { WORKSPACE_CHAT_FONT } from '../../constants/workspaceFonts';
import { isChatBlockedByActiveTool } from '../../utils/activeFormTools';

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
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [archiveOpenLocal, setArchiveOpenLocal] = useState(false);
  const archiveOpen = archiveOpenProp ?? archiveOpenLocal;
  const setArchiveOpen = onArchiveOpenChange ?? setArchiveOpenLocal;
  const {
    messages,
    loading,
    historyLoading,
    currentPhase,
    conversationId,
    activeTool,
    quotaExceeded,
    dismissQuotaModal,
    stationCheckpoint,
    dismissStationCheckpoint,
    sendMessage,
    loadConversation,
    startNewConversation,
    applyToolResponse,
  } = useChat(displayName);
  const { isRecording, livePreview, startRecording, stopRecording } = useVoiceRecord(i18n.language, getToken);
  const [recordingInputBase, setRecordingInputBase] = useState<string | null>(null);
  const chatLockedByForm = isChatBlockedByActiveTool(activeTool);

  useEffect(() => {
    if (!isRecording) setRecordingInputBase(null);
  }, [isRecording]);
  const chatToolRef = useRef<HTMLDivElement>(null);
  const messagesScrollRef = useRef<HTMLDivElement>(null);
  const { messagesEndRef, lastMessageRef } = useChatScrollIntoLatest(messages, loading || historyLoading);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isSendingRef = useRef(false);
  /** Matches WorkspaceMessageBubble: coach-aligned widgets on the same side as assistant bubbles. */
  const coachBubbleRowJustify = i18n.language.startsWith('he') ? 'justify-end' : 'justify-start';

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
    if (!activeTool) return;
    const t = window.setTimeout(() => {
      chatToolRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 120);
    return () => window.clearTimeout(t);
  }, [activeTool]);

  useEffect(() => {
    if (!chatLockedByForm || !isRecording) return;
    void (async () => {
      await stopRecording();
    })();
  }, [chatLockedByForm, isRecording, stopRecording]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;

    const init = async () => {
      setConversationsLoading(true);
      try {
        const token = (await getToken()) || apiClient.getToken();
        if (token) {
          apiClient.setToken(token);
          const convs = await apiClient.getConversations();
          setConversations(convs);
        }
      } catch (error) {
        console.error('Error initializing:', error);
      } finally {
        setConversationsLoading(false);
      }
    };
    init();
  }, [isLoaded, isSignedIn, getToken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (chatLockedByForm || !inputValue.trim() || loading || historyLoading || isSendingRef.current) return;
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
    if (chatLockedByForm) return;
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
  }, [chatLockedByForm, isRecording, inputValue, startRecording, stopRecording]);

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
      if (!chatLockedByForm) e.currentTarget.form?.requestSubmit();
    }
  };

  const displayValue =
    recordingInputBase !== null && isRecording
      ? `${recordingInputBase}${livePreview ? ' ' + livePreview : ''}`
      : inputValue;

  const isRTL = i18n.dir() === 'rtl';
  const onArchiveClick = useCallback(() => setArchiveOpen(true), []);

  const sessionPillLabel = useMemo(() => {
    if (conversationId == null || messages.length === 0) return null;
    const conv = conversations.find((c) => c.id === conversationId);
    if (!conv) return null;
    const sorted = [...conversations].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );
    const n = sorted.findIndex((c) => c.id === conversationId) + 1;
    if (n < 1) return null;
    const d = new Date(conv.created_at);
    const sod = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const isToday = sod(d) === sod(new Date());
    const locale = i18n.language.startsWith('he') ? 'he-IL' : 'en-US';
    const day = isToday
      ? t('chat.today')
      : d.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
    return t('chat.sessionPill', { day, n });
  }, [conversationId, conversations, messages.length, t, i18n.language]);

  const inputArea = (
    <>
      {conversationId != null && stationCheckpoint ? (
        <StationCheckpointBar
          checkpoint={stationCheckpoint}
          conversationId={conversationId}
          getToken={() => getToken()}
          onDismiss={dismissStationCheckpoint}
          onIntentSent={() => {}}
        />
      ) : null}
      <form
        onSubmit={handleSubmit}
        className="flex min-h-[48px] items-center gap-2 rounded-[11px] border border-[#e8e0cc] bg-white px-3 py-2 md:gap-3 md:px-4 md:py-2.5"
      >
        <textarea
          ref={inputRef}
          value={displayValue}
          onChange={(e) => {
            if (!isRecording && !chatLockedByForm) setInputValue(e.target.value);
          }}
          onKeyDown={handleKeyDown}
          placeholder={chatLockedByForm ? t('chat.formBlocksTyping') : t('chat.placeholder')}
          disabled={loading || historyLoading || isRecording || chatLockedByForm}
          className="min-h-[24px] max-h-28 flex-1 min-w-0 resize-none border-0 bg-transparent text-[14px] md:text-[16px] placeholder-[#4c5a70]/80 placeholder:text-[14px] focus:outline-none focus:ring-0 disabled:opacity-60"
          style={{
            fontFamily: WORKSPACE_CHAT_FONT,
            fontWeight: 400,
            lineHeight: 1.6,
            color: '#1a1510',
          }}
          rows={1}
        />
        <button
          type="button"
          onClick={handleMicClick}
          disabled={loading || historyLoading || chatLockedByForm}
          title={
            chatLockedByForm
              ? t('chat.formBlocksTyping')
              : isRecording
                ? t('chat.stopRecording')
                : t('chat.recordVoice')
          }
          className={`flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-[7px] border border-[rgba(255,255,255,0.11)] transition-colors ${
            isRecording
              ? 'bg-[#c8953a]/25 text-[#1e293b] border-[#c8953a]/35'
              : 'bg-[#e8e0cc] text-[#2E3A56]/85 hover:bg-[#ded6c4]'
          } disabled:opacity-50`}
        >
          {isRecording ? <Square size={13} strokeWidth={2} fill="currentColor" /> : <Mic size={13} strokeWidth={1.5} />}
        </button>
        <button
          type="submit"
          disabled={chatLockedByForm || !displayValue.trim() || loading || historyLoading || isRecording}
          className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-[7px] bg-[#1e293b] text-white transition-opacity hover:opacity-90 disabled:opacity-40"
          aria-label={t('chat.send')}
        >
          <Send size={13} strokeWidth={1.5} className="text-white" />
        </button>
      </form>
    </>
  );

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
          listLoading={conversationsLoading}
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
            loading={loading && !historyLoading}
            onArchiveClick={() => setArchiveOpen(true)}
            onNewChat={() => void handleNewChat()}
          />
        </div>

        {/* Archive Drawer */}
        <ArchiveDrawer
          isOpen={archiveOpen}
          onClose={() => setArchiveOpen(false)}
          conversations={conversations}
          listLoading={conversationsLoading}
          activeId={conversationId}
          onSelect={handleSelectConversation}
          onNewChat={handleNewChat}
          onDelete={handleDeleteConversation}
          onShare={handleShareConversation}
          isRTL={isRTL}
        />

        {/* Chat area: mobile [ strip | messages+input column ]; desktop messages row then full-width input */}
        <div className="order-1 md:order-2 flex flex-1 min-w-0 min-h-0 flex-col">
          {/* One row: full-height strip (mobile) + chat column. Desktop: strip hidden, chat is full width. */}
          <div className="flex flex-1 min-w-0 min-h-0 flex-row items-stretch min-h-0">
            {/* Mobile: stages strip — same height as messages+input (full workspace column) */}
            <div className="md:hidden flex h-full min-h-0 w-[78px] flex-shrink-0 self-stretch flex flex-col">
              <div className="flex-1 min-h-0 h-full max-h-full">
                <VisionLadder currentStep={currentPhase} onPhaseClick={handlePhaseClick} compact conversationId={conversationId} />
              </div>
            </div>
            <div className="flex min-w-0 min-h-0 flex-1 flex-col relative overflow-hidden bg-[#faf8f3]">
              <ShehiyaProgress loading={loading && !historyLoading} />
              {/* dir=ltr — ציר פיזי קבוע; יישור צד בועות לפי שפת הצ'אט ב-WorkspaceMessageBubble (עברית: מאמן מימין; אנגלית: מאמן משמאל). */}
              <div
                ref={messagesScrollRef}
                className="min-h-0 flex-1 overflow-y-auto px-3 py-4 md:px-10 md:py-10 custom-scrollbar bg-[#faf8f3] relative"
                dir="ltr"
              >
          {historyLoading && (
            <div
              className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[#faf8f3]/90 backdrop-blur-[2px] px-6"
              aria-busy="true"
              aria-live="polite"
            >
              <Loader2 className="h-9 w-9 text-[#AA771C] animate-spin" strokeWidth={2} />
              <p
                className="text-sm md:text-base text-[#2E3A56]/85 text-center max-w-sm font-medium"
                style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                dir={i18n.dir()}
              >
                {t('chat.loadingHistory')}
              </p>
            </div>
          )}
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
              {sessionPillLabel ? (
                <div className="flex justify-center pb-0 pt-1">
                  <div
                    className="rounded-full border border-[#e8e0cc] bg-[#f2ede2] px-3.5 py-1 text-[10px] font-normal uppercase tracking-[1.2px] text-[#8a7f6e]"
                    style={{ fontFamily: WORKSPACE_CHAT_FONT }}
                    dir={i18n.dir()}
                  >
                    {sessionPillLabel}
                  </div>
                </div>
              ) : null}
              <AnimatePresence>
                {messages.map((message, idx) => {
                  const phase = message.role === 'assistant' && message.meta?.phase
                    ? message.meta.phase
                    : messages.slice(0, idx).reverse().find(m => m.role === 'assistant' && m.meta?.phase)?.meta?.phase ?? 'S0';
                  return (
                    <div
                      key={message.id}
                      data-phase={phase}
                      data-message-id={message.id}
                      ref={idx === messages.length - 1 ? lastMessageRef : undefined}
                    >
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
                <div ref={chatToolRef} className={`flex ${coachBubbleRowJustify}`}>
                  <div
                    className="w-full max-w-[90%] md:max-w-[600px] rounded-[18px] border border-[#e8e0cc] bg-white px-5 py-4 md:px-6 md:py-5 shadow-[0px_1px_4px_rgba(10,10,10,0.06)]"
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
                <div className={`flex ${coachBubbleRowJustify}`}>
                  <div
                    className="flex items-center gap-3 rounded-[18px] border border-[#e8e0cc] bg-white px-5 py-4 shadow-[0px_1px_4px_rgba(10,10,10,0.06)]"
                  >
                    <div className="flex gap-1">
                      <span className="w-2.5 h-2.5 rounded-full bg-[#AA771C] animate-bounce shadow-sm" style={{ animationDelay: '0ms' }} />
                      <span className="w-2.5 h-2.5 rounded-full bg-[#AA771C] animate-bounce shadow-sm" style={{ animationDelay: '150ms' }} />
                      <span className="w-2.5 h-2.5 rounded-full bg-[#AA771C] animate-bounce shadow-sm" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span
                      className="text-[14px] font-medium text-[#4c5a70]"
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
              {/* Mobile: input only under chat, not under the blue strip */}
              <div className="md:hidden flex-shrink-0 border-t border-[#e8e0cc] bg-[#faf8f3] p-4">
                {inputArea}
              </div>
            </div>
          </div>

          {/* Desktop: input full width of chat column */}
          <div className="hidden md:block border-t border-[#e8e0cc] bg-[#faf8f3] p-4 md:p-9 flex-shrink-0">
            {inputArea}
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
