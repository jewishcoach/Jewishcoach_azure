import { useRef, useEffect } from 'react';
import { Heart, Send } from 'lucide-react';
import type { ChatMessage } from '../types';
import { MessageBubble } from '../components/MessageBubble';
import { ChatInput } from '../components/ChatInput';
import { useState } from 'react';

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

  // Initial state: only opening message — show centered card layout
  const isInitialState = messages.length === 1 && messages[0]?.role === 'assistant' && messages[0]?.id.startsWith('a-opening-');

  const handleSend = () => {
    if (!inputText.trim() || isLoading) return;
    onSend(inputText.trim());
    setInputText('');
  };

  if (isInitialState) {
    return (
      <div className="flex-1 flex flex-col min-h-0 pb-10 lg:pb-0">
        {/* Stage title */}
        {stageTitle && (
          <div className="py-6 text-center">
            <h2 className="text-2xl sm:text-3xl font-bold text-teal-800" style={{ fontFamily: "'Karantina', cursive" }}>
              שלב ראשון - {stageTitle}
            </h2>
          </div>
        )}

        {/* Centered elements — separate, not in a card */}
        <div className="flex-1 flex flex-col items-center px-4 sm:px-6 pt-4">
          <div className="w-full max-w-2xl space-y-4">
            {/* Coach label */}
            <div className="flex items-center gap-1.5 justify-end">
              <span className="text-sm font-semibold text-teal-700">בני</span>
              <Heart size={16} className="text-teal-400" />
            </div>

            {/* Coach question bubble */}
            <div className="w-full bg-white rounded-2xl py-5 px-6 shadow-sm">
              <p className="text-base text-gray-800 text-end leading-relaxed">
                {messages[0].content}
              </p>
            </div>

            {/* Quick-reply chips — 4 in a row, equal width */}
            {quickReplies && (
              <div className="grid grid-cols-4 gap-3">
                {quickReplies.map((reply) => (
                  <button
                    key={reply}
                    type="button"
                    onClick={() => onSend(reply)}
                    className="py-3 px-2 rounded-2xl border border-teal-200 bg-teal-50/50 text-sm text-teal-800
                               hover:bg-teal-100 hover:border-teal-300 transition-colors text-center"
                  >
                    {reply}
                  </button>
                ))}
              </div>
            )}

            {/* Input row — send on left (start), input on right */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleSend}
                disabled={isLoading || !inputText.trim()}
                className="flex-shrink-0 w-10 h-10 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center
                           disabled:opacity-40 hover:bg-teal-200 transition-colors"
              >
                <Send size={18} className="rtl:-scale-x-100" />
              </button>
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="כתוב את תשובתך כאן, או בחר מהאפשרויות למעלה..."
                className="flex-1 px-5 py-3 rounded-full border border-gray-200 bg-white text-sm text-gray-700
                           placeholder:text-gray-400 focus:outline-none focus:border-teal-400"
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Regular chat flow (after user responds)
  return (
    <div className="flex-1 flex flex-col min-h-0 pb-10 lg:pb-0">
      {/* Stage title banner */}
      {stageTitle && (
        <div className="py-3 border-b border-gray-100 bg-white/60">
          <h2 className="text-xl sm:text-2xl font-bold text-teal-800 text-center" style={{ fontFamily: "'Karantina', cursive" }}>
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
              <span className="text-xs font-semibold text-teal-700">בני</span>
              <Heart size={12} className="text-teal-500 fill-teal-500" />
            </div>
            <div className="px-4 py-3 rounded-2xl rounded-ee-sm bg-white border border-gray-200 text-sm text-gray-400 shadow-sm">
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
