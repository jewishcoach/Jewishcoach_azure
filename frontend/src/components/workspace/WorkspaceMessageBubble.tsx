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
          max-w-[85%] rounded-[4px] px-5 py-4
          ${isUser
            ? 'border-r-2 border-[#991B1B] bg-transparent'
            : ''
          }
        `}
        style={!isUser ? {
          background: 'rgba(255,255,255,0.04)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          border: '0.5px solid rgba(212, 175, 55, 0.3)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(212,175,55,0.05)',
        } : undefined}
      >
        <div className={`prose prose-sm max-w-none ${isUser ? 'prose-invert text-white/95' : 'text-white/90'}`} style={{ fontFamily: 'Inter, sans-serif', fontWeight: 300, lineHeight: 1.6 }}>
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed text-[15px]" style={{ lineHeight: 1.6 }}>{children}</p>,
              ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1.5 text-[15px]" style={{ lineHeight: 1.6 }}>{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1.5 text-[15px]" style={{ lineHeight: 1.6 }}>{children}</ol>,
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
