import { useRef, useEffect, useState, useCallback } from 'react';
import { Heart, Send } from 'lucide-react';
import type { V3ChatMessage, ActiveInlineTool, ChatMessage } from '../types';
import { MessageBubble } from '../../v2/components/MessageBubble';
import { SafetyMessage } from '../components/SafetyMessage';
import { getConceptAudioForMessage } from '../../v2/components/conceptAudio';
import { InlineTool } from '../components/InlineTool';
import { CompletedToolCard } from '../components/CompletedToolCard';

const STAGE_ORDINAL_HE = ['', 'ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי'];

interface ChatScreenProps {
  messages: V3ChatMessage[];
  onSend: (message: string) => void;
  isLoading: boolean;
  stageTitle?: string;
  stageNumber?: number;
  currentStep?: string;
  activeTool: ActiveInlineTool | null;
  toolSubmitting: boolean;
  onSubmitTool: (toolType: string, data: Record<string, unknown>) => void;
  onDismissTool: () => void;
  /** Set when the stage just ended: show a button to open the stage summary */
  onShowSummary?: () => void;
}

export function ChatScreen({
  messages,
  onSend,
  isLoading,
  stageTitle,
  stageNumber = 1,
  currentStep = 'S0',
  activeTool,
  toolSubmitting,
  onSubmitTool,
  onDismissTool,
  onShowSummary,
}: ChatScreenProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputBarRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const [inputText, setInputText] = useState('');
  const [playedAudioFiles] = useState(() => new Set<string>());
  const [messageAudioMap] = useState(() => new Map<string, { file: string; label: string }>());

  const inputDisabled = !!activeTool || isLoading || !!onShowSummary;

  // Mobile: the input bar is fixed over the page — reserve exactly its height (it grows with multi-line
  // input) so the bottom of the last card (its submit button) is never hidden behind it.
  useEffect(() => {
    const bar = inputBarRef.current;
    const root = rootRef.current;
    if (!bar || !root || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => root.style.setProperty('--input-bar-h', `${bar.offsetHeight}px`));
    ro.observe(bar);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const onResize = () => {
      if (inputBarRef.current) {
        const offset = window.innerHeight - vv.height - vv.offsetTop;
        inputBarRef.current.style.bottom = `${Math.max(0, offset)}px`;
      }
    };
    vv.addEventListener('resize', onResize);
    vv.addEventListener('scroll', onResize);
    return () => {
      vv.removeEventListener('resize', onResize);
      vv.removeEventListener('scroll', onResize);
    };
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages.length, activeTool]);

  const chatMessages = messages.filter((m) => m.role !== 'tool_result');
  // Drop only an immediate double-send (same user text twice in a row, no coach reply between).
  // A user may legitimately give the same answer again later ("כן", a quick reply) — that must stay visible.
  const dedupedMessages = messages.filter((msg, i) => {
    if (msg.role !== 'user') return true;
    const prev = messages[i - 1];
    return !(prev && prev.role === 'user' && prev.content === msg.content);
  });
  const lastMessage = chatMessages[chatMessages.length - 1];
  const showQuickReplies = lastMessage?.role === 'assistant' && !isLoading && !activeTool;
  const quickReplies = showQuickReplies ? lastMessage.suggestions : undefined;

  const sendingRef = useRef(false);
  useEffect(() => {
    if (!isLoading) sendingRef.current = false;
  }, [isLoading]);
  const handleSend = useCallback(() => {
    if (!inputText.trim() || inputDisabled || sendingRef.current) return;
    sendingRef.current = true;
    onSend(inputText.trim());
    setInputText('');
  }, [inputText, inputDisabled, onSend]);

  return (
    <div ref={rootRef} className="flex-1 flex flex-col min-h-0 pb-[var(--input-bar-h,56px)] lg:pb-0">
      {/* Stage title */}
      {stageTitle && (
        <div className="pt-4 lg:pt-6 flex justify-center">
          <div className="w-full max-w-[662px] px-5 lg:px-4">
            <h2
              className="text-[32px] lg:text-[40px] text-[#2d4658] text-center"
              style={{ fontFamily: "'Karantina', cursive", lineHeight: '1.2' }}
            >
              שלב {STAGE_ORDINAL_HE[stageNumber] || stageNumber} - {stageTitle}
            </h2>
          </div>
        </div>
      )}

      {/* Messages + inline tools area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto py-4 flex flex-col items-center"
      >
        <div className="w-full max-w-[662px] px-5 lg:px-4 space-y-6">
          {dedupedMessages.map((msg, idx) => {
            // Render completed tool cards
            if (msg.role === 'tool_result' && msg.toolResult) {
              return (
                <CompletedToolCard key={msg.id} result={msg.toolResult} />
              );
            }

            const isLastAssistant = showQuickReplies && msg.role === 'assistant' && msg.id === lastMessage?.id;

            if (msg.safety) {
              return <SafetyMessage key={msg.id} content={msg.content} onQuickReply={isLastAssistant ? onSend : undefined} />;
            }

            const prevDeduped = idx > 0 ? dedupedMessages[idx - 1] : null;
            const nextDeduped = idx < dedupedMessages.length - 1 ? dedupedMessages[idx + 1] : null;
            const prevHadSuggestions = prevDeduped?.role === 'assistant' && prevDeduped.suggestions?.length;
            const isSelectedReply = msg.role === 'user' && prevHadSuggestions;

            const hasUserReply = msg.role === 'assistant' && nextDeduped?.role === 'user';
            const repliesForCompleted = hasUserReply && msg.suggestions?.length ? msg.suggestions : undefined;

            if (isSelectedReply) return null;

            let conceptAudio = null;
            if (msg.role === 'assistant') {
              if (messageAudioMap.has(msg.id)) {
                conceptAudio = messageAudioMap.get(msg.id)!;
              } else {
                const step = msg.phase || currentStep;
                conceptAudio = getConceptAudioForMessage(step, msg.content, playedAudioFiles);
                if (conceptAudio) {
                  playedAudioFiles.add(conceptAudio.file);
                  messageAudioMap.set(msg.id, conceptAudio);
                }
              }
            }

            return (
              <MessageBubble
                key={msg.id}
                message={msg as ChatMessage}
                quickReplies={isLastAssistant ? quickReplies : repliesForCompleted}
                onQuickReply={isLastAssistant ? onSend : undefined}
                selectedReply={hasUserReply && repliesForCompleted ? nextDeduped!.content : undefined}
                conceptAudio={conceptAudio}
              />
            );
          })}

          {/* Loading indicator — shows during chat AND after tool submission */}
          {(isLoading || toolSubmitting) && !activeTool && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2" dir="rtl">
                <Heart size={16} className="text-[#03ffe6]" />
                <span className="text-sm text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>בני</span>
              </div>
              <div className="px-4 py-3 rounded-xl bg-white text-sm text-gray-400 shadow-[0px_0px_3.35px_rgba(0,0,0,0.08)] w-fit">
                <span className="inline-flex gap-1">
                  <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
                  <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
                  <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
                </span>
              </div>
            </div>
          )}

          {/* Stage ended — closing message is above; summary opens on click */}
          {onShowSummary && !isLoading && !toolSubmitting && (
            <div className="flex justify-center animate-[fadeIn_0.3s_ease-out]">
              <button
                type="button"
                onClick={onShowSummary}
                className="w-[239px] h-[53px] rounded-xl bg-[#9747ff] text-white text-base hover:bg-[#8035e6] drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)] transition-colors"
                style={{ fontFamily: "'Heebo', sans-serif" }}
              >
                להמשך לסיכום השלב
              </button>
            </div>
          )}

          {/* Active inline tool */}
          {activeTool && (
            <div className="animate-[fadeIn_0.3s_ease-out]">
              <InlineTool
                tool={activeTool}
                onSubmit={onSubmitTool}
                isSubmitting={toolSubmitting}
              />
            </div>
          )}
        </div>
      </div>

      {/* Input bar */}
      <div ref={inputBarRef} className="fixed bottom-0 inset-x-0 lg:relative bg-white p-3 pb-5 lg:pb-3 flex flex-col items-center z-20" dir="rtl">
        <div className="flex items-center gap-3 w-full max-w-[663px] px-2 lg:px-0 flex-row-reverse">
          <button
            type="button"
            onClick={handleSend}
            disabled={inputDisabled || !inputText.trim()}
            className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-colors
              ${!inputDisabled && inputText.trim()
                ? 'bg-[#03ffe6] text-[#2d4658] hover:bg-[#02e6d0]'
                : 'bg-[rgba(3,255,230,0.2)] text-[rgba(45,70,88,0.4)]'
              }`}
          >
            <Send size={16} />
          </button>
          <div className="flex-1">
            <textarea
              dir="auto"
              value={inputText}
              onChange={(e) => {
                setInputText(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
              }}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder={activeTool ? 'מלא את הכרטיס למעלה...' : 'כתוב את תשובתך כאן...'}
              disabled={!!activeTool}
              rows={1}
              className={`w-full px-4 py-3 rounded-xl border-[0.8px] bg-white text-base text-[#2d4658]
                         placeholder:text-[rgba(45,70,88,0.4)] focus:outline-none
                         shadow-[0px_0px_6.7px_0px_rgba(0,0,0,0.08)] text-right resize-none
                         min-h-[46px] max-h-[120px] overflow-y-auto transition-colors
                         ${activeTool ? 'border-[#d2d2d2] bg-[#f6f4f0] cursor-not-allowed' : 'border-[#03ffe6]'}`}
              style={{ fontFamily: "'Heebo', sans-serif" }}
            />
          </div>
        </div>
        {/* Skip tool link */}
        {activeTool && (
          <button
            type="button"
            onClick={onDismissTool}
            className="mt-2 text-xs text-[rgba(45,70,88,0.4)] hover:text-[#2d4658] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            אני מעדיף לכתוב
          </button>
        )}
      </div>
    </div>
  );
}
