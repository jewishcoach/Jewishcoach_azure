import { useRef, useEffect, useState } from 'react';
import { Heart, Send } from 'lucide-react';
import type { ChatMessage } from '../types';
import { MessageBubble } from '../components/MessageBubble';
import { ChatInput } from '../components/ChatInput';

interface ChatScreenProps {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  isLoading: boolean;
  stageTitle?: string;
}

export function ChatScreen({ messages, onSend, isLoading, stageTitle }: ChatScreenProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [inputText, setInputText] = useState('');

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages.length]);

  const lastMessage = messages[messages.length - 1];
  const showQuickReplies = lastMessage?.role === 'assistant' && !isLoading;
  const quickReplies = showQuickReplies ? getQuickRepliesForMessage(lastMessage) : undefined;

  const isInitialState = messages.length === 1 && messages[0]?.role === 'assistant' && messages[0]?.id.startsWith('a-opening-');

  const handleSend = () => {
    if (!inputText.trim() || isLoading) return;
    onSend(inputText.trim());
    setInputText('');
  };

  if (isInitialState) {
    return (
      <div className="flex-1 flex flex-col min-h-0 pb-10 lg:pb-0">
        {/* Stage title — aligned right */}
        {stageTitle && (
          <div className="pt-8 pe-6">
            <h2
              className="text-[40px] text-[#2d4658] text-right"
              style={{ fontFamily: "'Karantina', cursive", lineHeight: '77px' }}
            >
              שלב ראשון - {stageTitle}
            </h2>
          </div>
        )}

        {/* Content aligned to end (right in RTL) */}
        <div className="flex-1 flex flex-col items-end px-6 pt-6">
          <div className="w-full max-w-[662px] space-y-5">
            {/* Coach label */}
            <div className="flex items-center gap-2 justify-end">
              <span className="text-sm text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>בני</span>
              <Heart size={16} className="text-[#03ffe6]" />
            </div>

            {/* Coach question bubble */}
            <div className="w-full bg-white rounded-xl py-4 px-3 shadow-[0px_0px_3.35px_rgba(0,0,0,0.08)] flex items-center justify-end">
              <p
                className="text-base font-semibold text-[#2d4658] text-right w-[373px] leading-[22.5px]"
                style={{ fontFamily: "'Assistant', sans-serif" }}
              >
                {messages[0].content}
              </p>
            </div>

            {/* Quick-reply chips — 4 in a row */}
            {quickReplies && (
              <div className="flex gap-3">
                {quickReplies.map((reply) => (
                  <button
                    key={reply}
                    type="button"
                    onClick={() => onSend(reply)}
                    className="flex-1 h-[34px] rounded-xl border border-[#03ffe6] bg-[rgba(3,255,230,0.05)]
                               text-base font-semibold text-[#2d4658] text-center
                               hover:bg-[rgba(3,255,230,0.15)] transition-colors"
                    style={{ fontFamily: "'Assistant', sans-serif" }}
                  >
                    {reply}
                  </button>
                ))}
              </div>
            )}

            {/* Input row */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleSend}
                disabled={isLoading || !inputText.trim()}
                className="flex-shrink-0 w-10 h-10 rounded-xl bg-[#03ffe6] text-[#2d4658] flex items-center justify-center
                           disabled:opacity-40 hover:bg-[#02e6d0] transition-colors"
              >
                <Send size={16} className="rtl:-scale-x-100" />
              </button>
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="כתוב את תשובתך כאן, או בחר מהאפשרויות למעלה..."
                  className="w-full px-3 py-3 rounded-xl bg-white text-base text-[#2d4658]
                             placeholder:text-[rgba(45,70,88,0.4)] focus:outline-none
                             shadow-[0px_0px_6.7px_0px_rgba(0,0,0,0.08)] text-right"
                  style={{ fontFamily: "'Heebo', sans-serif" }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Regular chat flow
  return (
    <div className="flex-1 flex flex-col min-h-0 pb-10 lg:pb-0">
      {/* Stage title banner */}
      {stageTitle && (
        <div className="py-3 pe-6">
          <h2
            className="text-[40px] text-[#2d4658] text-right"
            style={{ fontFamily: "'Karantina', cursive", lineHeight: '77px' }}
          >
            שלב ראשון - {stageTitle}
          </h2>
        </div>
      )}

      {/* Messages area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-4"
      >
        {messages.map((msg, idx) => {
          const isLastAssistant = showQuickReplies && idx === messages.length - 1 && msg.role === 'assistant';

          return (
            <MessageBubble
              key={msg.id}
              message={msg}
              quickReplies={isLastAssistant ? getQuickRepliesForMessage(msg) : undefined}
              onQuickReply={onSend}
            />
          );
        })}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex flex-col items-end gap-1">
            <div className="flex items-center gap-1.5 pe-1">
              <span className="text-xs font-semibold text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>בני</span>
              <Heart size={12} className="text-[#03ffe6]" />
            </div>
            <div className="px-4 py-3 rounded-xl bg-white text-sm text-gray-400 shadow-[0px_0px_3.35px_rgba(0,0,0,0.08)]">
              <span className="inline-flex gap-1">
                <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
                <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
                <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Input bar */}
      <ChatInput onSend={onSend} disabled={isLoading} />
    </div>
  );
}

function getQuickRepliesForMessage(msg: ChatMessage): string[] | undefined {
  if (msg.id.startsWith('a-opening-')) {
    return ['זה משפיע על הביטחון שלי', 'אני מרגיש שאני נתקע', 'קשה לי עם אנשים מסוימים', 'משהו אחר'];
  }
  return undefined;
}
