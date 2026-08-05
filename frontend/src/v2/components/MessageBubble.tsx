import { Heart } from 'lucide-react';
import type { ChatMessage } from '../types';

interface MessageBubbleProps {
  message: ChatMessage;
  quickReplies?: string[];
  onQuickReply?: (text: string) => void;
}

export function MessageBubble({ message, quickReplies, onQuickReply }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-start">
        <div
          className="max-w-[75%] px-4 py-3 rounded-xl bg-[rgba(3,255,230,0.15)] border border-[#03ffe6] text-base text-[#2d4658] leading-[22.75px] text-right"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-end gap-2">
      {/* Coach label */}
      <div className="flex items-center gap-2 pe-1">
        <span className="text-sm text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>בני</span>
        <Heart size={14} className="text-[#03ffe6]" />
      </div>

      {/* Message bubble */}
      <div
        className="max-w-[75%] px-4 py-3 rounded-xl bg-white text-base leading-[22.75px] text-[#2d4658] text-right shadow-[0px_0px_3.35px_rgba(0,0,0,0.08)]"
        style={{ fontFamily: "'Heebo', sans-serif" }}
      >
        {message.content}
      </div>

      {/* Quick-reply chips */}
      {quickReplies && quickReplies.length > 0 && (
        <div className="flex gap-3 mt-1 w-full">
          {quickReplies.map((reply) => (
            <button
              key={reply}
              type="button"
              onClick={() => onQuickReply?.(reply)}
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
    </div>
  );
}
