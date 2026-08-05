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
          className="max-w-[75%] px-4 py-3 rounded-xl bg-[#03ffe6] text-[#2d4658] text-base leading-[22.75px] shadow-sm"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      {/* Coach label */}
      <div className="flex items-center gap-1.5 pe-1">
        <span className="text-sm text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>בני</span>
        <Heart size={14} className="text-[#03ffe6]" />
      </div>

      {/* Message bubble */}
      <div
        className="max-w-[75%] px-4 py-3 rounded-xl bg-white text-base leading-[22.75px] text-[#2d4658] shadow-[0px_0px_3.35px_rgba(0,0,0,0.08)]"
        style={{ fontFamily: "'Heebo', sans-serif" }}
      >
        {message.content}
      </div>

      {/* Quick-reply chips */}
      {quickReplies && quickReplies.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2 justify-end max-w-[90%]">
          {quickReplies.map((reply) => (
            <button
              key={reply}
              type="button"
              onClick={() => onQuickReply?.(reply)}
              className="px-4 py-2 rounded-xl border border-[#d2d2d2] text-sm text-[#2d4658]
                         bg-[rgba(255,255,255,0.3)] hover:border-[#04c4b1] hover:bg-[rgba(3,255,230,0.1)]
                         transition-colors"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {reply}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
