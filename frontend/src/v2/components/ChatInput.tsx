import { useState } from 'react';
import { Send } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  const [text, setText] = useState('');

  const handleSubmit = () => {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText('');
  };

  return (
    <div className="px-4 py-3 bg-white border-t border-gray-100">
      <div className="flex items-center gap-2 max-w-3xl mx-auto">
        {/* Send button on the START side (left in RTL visual) */}
        <button
          type="button"
          onClick={handleSubmit}
          disabled={disabled || !text.trim()}
          className="flex-shrink-0 w-10 h-10 rounded-full bg-teal-500 text-white flex items-center justify-center
                     disabled:opacity-40 disabled:cursor-not-allowed hover:bg-teal-600 transition-colors shadow-sm"
        >
          <Send size={18} className="rtl:-scale-x-100" />
        </button>

        {/* Input field */}
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          disabled={disabled}
          placeholder={placeholder ?? 'כתוב את תשובתך כאן, או בחר מהאפשרויות למעלה...'}
          className="flex-1 px-4 py-2.5 rounded-full border border-teal-300 text-sm text-gray-700
                     placeholder:text-gray-400 focus:outline-none focus:border-teal-500 focus:ring-1
                     focus:ring-teal-500/20 disabled:bg-gray-50 transition-colors"
        />
      </div>
    </div>
  );
}
