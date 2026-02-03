import type { Message } from '../types';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';

interface Props {
  message: Message;
}

export const MessageBubble = ({ message }: Props) => {
  const isUser = message.role === 'user';

  return (
    <motion.div 
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      initial={{ opacity: 0, x: isUser ? 20 : -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div
        className={`
          max-w-[95%] rounded-2xl px-5 py-4 shadow-md
          ${isUser
            ? 'bg-gradient-to-br from-primary to-primary-light text-white'
            : 'bg-white/90 backdrop-blur-sm text-gray-900 border-s-4 border-accent shadow-glass'
          }
        `}
      >
        <div className={`prose prose-sm max-w-none ${isUser ? 'prose-invert' : ''}`}>
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
              ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
              li: ({ children }) => <li className="mb-1">{children}</li>,
              strong: ({ children }) => <strong className={isUser ? 'text-white font-bold' : 'text-accent-dark font-bold'}>{children}</strong>,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        <div className={`text-xs mt-2 ${isUser ? 'text-blue-100' : 'text-gray-500'}`}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </motion.div>
  );
};
