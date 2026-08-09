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
    <div className="flex-1 flex flex-col min-h-0 pb-14 lg:pb-0">
      {/* Stage title */}
      {stageTitle && (
        <div className="pt-4 lg:pt-6 flex justify-center">
          <div className="w-full max-w-[662px] px-5 lg:px-4">
            <h2
              className="text-[32px] lg:text-[40px] text-[#2d4658] text-center"
              style={{ fontFamily: "'Karantina', cursive", lineHeight: '1.2' }}
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
        <div className="w-full max-w-[662px] px-5 lg:px-4 space-y-6">
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
      <div className="fixed bottom-0 inset-x-0 lg:relative bg-white p-3 pb-5 lg:pb-3 flex items-center justify-center z-20" dir="ltr">
        <div className="flex items-center gap-3 w-full max-w-[663px] px-2 lg:px-0">
          <button
            type="button"
            onClick={handleSend}
            disabled={isLoading || !inputText.trim()}
            className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-colors
              ${inputText.trim()
                ? 'bg-[#03ffe6] text-[#2d4658] hover:bg-[#02e6d0]'
                : 'bg-[rgba(3,255,230,0.2)] text-[rgba(45,70,88,0.4)]'
              }`}
          >
            <Send size={16} />
          </button>
          <div className="flex-1">
            <textarea
              value={inputText}
              onChange={(e) => {
                setInputText(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
              }}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder="כתוב את תשובתך כאן, או בחר מהאפשרויות למעלה..."
              rows={1}
              className="w-full px-4 py-3 rounded-xl border-[0.8px] border-[#03ffe6] bg-white text-base text-[#2d4658]
                         placeholder:text-[rgba(45,70,88,0.4)] focus:outline-none
                         shadow-[0px_0px_6.7px_0px_rgba(0,0,0,0.08)] text-right resize-none
                         min-h-[46px] max-h-[120px] overflow-y-auto"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function getQuickRepliesForMessage(_msg: ChatMessage): string[] | undefined {
  return undefined;
}
