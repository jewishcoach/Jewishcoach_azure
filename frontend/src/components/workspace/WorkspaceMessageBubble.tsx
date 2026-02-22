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
          max-w-[85%] rounded-[4px] px-9 py-6
          ${isUser ? '' : ''}
        `}
        style={{
          background: isUser ? 'rgba(255, 255, 255, 0.02)' : 'rgba(255, 255, 255, 0.03)',
          backdropFilter: 'blur(25px)',
          WebkitBackdropFilter: 'blur(25px)',
          border: isUser ? '0.5px solid rgba(255, 255, 255, 0.08)' : '0.5px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 12px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.03)',
          ...(isUser && { borderRight: '2px solid rgba(212, 175, 55, 0.4)' }),
        }}
      >
        <div className={`prose prose-sm max-w-none ${isUser ? 'prose-invert' : ''}`} style={{ fontFamily: 'Inter, sans-serif', fontWeight: 300, lineHeight: 1.6, color: isUser ? 'rgba(245,245,240,0.95)' : 'rgba(245,245,240,0.92)' }}>
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-4 last:mb-0 leading-relaxed text-[16px]" style={{ lineHeight: 1.7 }}>{children}</p>,
              ul: ({ children }) => <ul className="list-disc list-inside mb-4 space-y-2 text-[16px]" style={{ lineHeight: 1.7 }}>{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside mb-4 space-y-2 text-[16px]" style={{ lineHeight: 1.7 }}>{children}</ol>,
              li: ({ children }) => <li className="mb-1">{children}</li>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        <div className={`text-[11px] mt-2 ${isUser ? 'text-[#F5F5F0]/50' : 'text-[#F5F5F0]/40'}`}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </motion.div>
  );
};
