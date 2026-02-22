import type { Message } from '../../types';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';

interface Props {
  message: Message;
}

export const WorkspaceMessageBubble = ({ message }: Props) => {
  const isUser = message.role === 'user';

  return (
    <motion.div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div
        className={`
          max-w-[85%] rounded-[4px] px-4 py-3
          ${isUser
            ? 'border-r-2 border-[#991B1B] bg-transparent'
            : 'bg-white/10 backdrop-blur-xl border border-amber-500/20'
          }
        `}
      >
        <div className={`prose prose-sm max-w-none ${isUser ? 'prose-invert text-white/95' : 'text-white/90'}`}>
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed text-sm">{children}</p>,
              ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1 text-sm">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1 text-sm">{children}</ol>,
              li: ({ children }) => <li className="mb-1">{children}</li>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        <div className={`text-[10px] mt-1.5 ${isUser ? 'text-white/50' : 'text-white/40'}`}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </motion.div>
  );
};
