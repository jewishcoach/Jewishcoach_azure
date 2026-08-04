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
        <div className="max-w-[75%] px-4 py-3 rounded-2xl rounded-es-sm bg-teal-500 text-white text-sm leading-relaxed shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  // Coach (assistant) message
  return (
    <div className="flex flex-col items-end gap-1">
      {/* Coach label */}
      <div className="flex items-center gap-1.5 pe-1">
        <span className="text-xs font-semibold text-teal-700">בני</span>
        <Heart size={12} className="text-teal-500 fill-teal-500" />
      </div>

      {/* Message bubble */}
      <div className="max-w-[75%] px-4 py-3 rounded-2xl rounded-ee-sm bg-white border border-gray-200 text-sm leading-relaxed text-gray-800 shadow-sm">
        {message.content}
      </div>

      {/* Quick-reply chips (shown below the coach message) */}
      {quickReplies && quickReplies.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2 justify-end max-w-[90%]">
          {quickReplies.map((reply) => (
            <button
              key={reply}
              type="button"
              onClick={() => onQuickReply?.(reply)}
              className="px-4 py-2 rounded-full border border-teal-400 text-sm text-teal-700
                         bg-white hover:bg-teal-50 hover:border-teal-500 transition-colors"
            >
              {reply}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
