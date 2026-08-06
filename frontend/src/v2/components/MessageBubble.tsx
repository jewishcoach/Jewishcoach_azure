import { Heart } from 'lucide-react';
import type { ChatMessage } from '../types';

interface MessageBubbleProps {
  message: ChatMessage;
  quickReplies?: string[];
  onQuickReply?: (text: string) => void;
  selectedReply?: string;
}

export function MessageBubble({ message, quickReplies, onQuickReply, selectedReply }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-start" dir="rtl">
        <div
          className="px-6 h-[34px] flex items-center justify-center rounded-tl-xl rounded-tr-xl rounded-bl-xl bg-[#03ffe6] border border-[#03ffe6] text-base font-semibold text-[#2d4658]"
          style={{ fontFamily: "'Assistant', sans-serif" }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 w-full" dir="rtl">
      {/* Coach label */}
      <div className="flex items-center gap-2 justify-start">
        <Heart size={16} className="text-[#03ffe6]" />
        <span className="text-sm text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>בני</span>
      </div>

      {/* Message bubble — full width */}
      <div className="w-full bg-white rounded-xl py-4 px-4 shadow-[0px_0px_3.35px_rgba(0,0,0,0.08)]">
        <p
          className="text-base text-[#2d4658] text-right leading-[22.75px]"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          {message.content}
        </p>
      </div>

      {/* Quick-reply chips — equal width, single row */}
      {quickReplies && quickReplies.length > 0 && (
        <div className="flex gap-3 w-full">
          {quickReplies.map((reply) => (
            <button
              key={reply}
              type="button"
              onClick={() => onQuickReply?.(reply)}
              className="flex-1 h-[34px] rounded-xl border-[0.8px] border-[#03ffe6] bg-[rgba(3,255,230,0.05)]
                         text-base font-semibold text-[#2d4658] text-center whitespace-nowrap
                         hover:bg-[rgba(3,255,230,0.15)] transition-colors"
              style={{ fontFamily: "'Assistant', sans-serif" }}
            >
              {reply}
            </button>
          ))}
        </div>
      )}

      {/* Selected reply shown below chips */}
      {selectedReply && (
        <div className="flex justify-start w-full">
          <div
            className="px-6 h-[34px] flex items-center justify-center rounded-tl-xl rounded-tr-xl rounded-bl-xl bg-[#03ffe6] border border-[#03ffe6] text-base font-semibold text-[#2d4658]"
            style={{ fontFamily: "'Assistant', sans-serif" }}
          >
            {selectedReply}
          </div>
        </div>
      )}
    </div>
  );
}
