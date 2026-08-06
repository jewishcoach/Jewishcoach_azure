import { useRef, useEffect, useState } from 'react';
import { Heart, Send } from 'lucide-react';
import type { ChatMessage } from '../types';
import { MessageBubble } from '../components/MessageBubble';

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
  const quickReplies = showQuickReplies ? (lastMessage.suggestions?.length ? lastMessage.suggestions : getQuickRepliesForMessage(lastMessage)) : undefined;

  const handleSend = () => {
    if (!inputText.trim() || isLoading) return;
    onSend(inputText.trim());
    setInputText('');
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 pb-10 lg:pb-0">
      {/* Stage title */}
      {stageTitle && (
        <div className="pt-6 flex justify-center">
          <div className="w-full max-w-[662px] px-4">
            <h2
              className="text-[40px] text-[#2d4658] text-center"
              style={{ fontFamily: "'Karantina', cursive", lineHeight: '77px' }}
            >
              שלב ראשון - {stageTitle}
            </h2>
          </div>
        </div>
      )}

      {/* Messages area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto py-4 flex flex-col items-center"
      >
        <div className="w-full max-w-[662px] px-4 space-y-6">
          {messages.map((msg, idx) => {
            const isLastAssistant = showQuickReplies && idx === messages.length - 1 && msg.role === 'assistant';

            // For user messages following an assistant with suggestions,
            // the user message is the "selected reply" shown as a teal chip
            const prevMsg = idx > 0 ? messages[idx - 1] : null;
            const prevHadSuggestions = prevMsg?.role === 'assistant' && (prevMsg.suggestions?.length || getQuickRepliesForMessage(prevMsg));
            const isSelectedReply = msg.role === 'user' && prevHadSuggestions;

            // Show chips on the assistant message that preceded a user selection
            const nextMsg = idx < messages.length - 1 ? messages[idx + 1] : null;
            const hasUserReply = msg.role === 'assistant' && nextMsg?.role === 'user';
            const msgSuggestions = msg.suggestions?.length ? msg.suggestions : getQuickRepliesForMessage(msg);
            const repliesForCompleted = hasUserReply ? msgSuggestions : undefined;

            if (isSelectedReply) {
              // User's reply is already shown as selectedReply on the previous assistant bubble
              return null;
            }

            return (
              <MessageBubble
                key={msg.id}
                message={msg}
                quickReplies={isLastAssistant ? quickReplies : repliesForCompleted}
                onQuickReply={isLastAssistant ? onSend : undefined}
                selectedReply={hasUserReply && repliesForCompleted ? nextMsg!.content : undefined}
              />
            );
          })}

          {/* Loading indicator */}
          {isLoading && (
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
        </div>
      </div>

      {/* Input bar — fixed at bottom */}
      <div className="bg-white p-3 flex items-center justify-center">
        <div className="flex items-center gap-3 w-full max-w-[663px]">
          <button
            type="button"
            onClick={handleSend}
            disabled={isLoading || !inputText.trim()}
            className="flex-shrink-0 w-10 h-10 rounded-xl bg-[#03ffe6] text-[#2d4658] flex items-center justify-center
                       disabled:opacity-40 hover:bg-[#02e6d0] transition-colors"
          >
            <Send size={16} className="rtl:-scale-x-100" />
          </button>
          <div className="flex-1">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="כתוב את תשובתך כאן, או בחר מהאפשרויות למעלה..."
              className="w-full px-4 py-3 rounded-xl border-[0.8px] border-[#03ffe6] bg-white text-base text-[#2d4658]
                         placeholder:text-[rgba(45,70,88,0.4)] focus:outline-none
                         shadow-[0px_0px_6.7px_0px_rgba(0,0,0,0.08)] text-right"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function getQuickRepliesForMessage(msg: ChatMessage): string[] | undefined {
  if (msg.id.startsWith('a-opening-')) {
    return ['עבודה', 'משפחה וקשרים', 'בריאות ורווחה', 'אחר'];
  }
  return undefined;
}
