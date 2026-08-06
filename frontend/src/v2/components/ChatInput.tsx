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
    <div className="bg-white p-3 flex items-center justify-center">
      <div className="flex items-center gap-3 w-full max-w-[663px]">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={disabled || !text.trim()}
          className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-colors
            ${text.trim()
              ? 'bg-[#03ffe6] text-[#2d4658] hover:bg-[#02e6d0]'
              : 'bg-[rgba(3,255,230,0.2)] text-[rgba(45,70,88,0.4)]'
            }`}
        >
          <Send size={16} className="rtl:-scale-x-100" />
        </button>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          disabled={disabled}
          placeholder={placeholder ?? 'כתוב את תשובתך כאן, או בחר מהאפשרויות למעלה...'}
          className="flex-1 px-4 py-3 rounded-xl border border-[#03ffe6] bg-white text-base text-[#2d4658]
                     placeholder:text-[rgba(45,70,88,0.4)] focus:outline-none
                     shadow-[0px_0px_6.7px_0px_rgba(0,0,0,0.08)] text-end
                     disabled:bg-gray-50 transition-colors"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        />
      </div>
    </div>
  );
}
