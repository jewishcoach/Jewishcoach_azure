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
      className={`flex ${isUser ? 'justify-start' : 'justify-end'}`}
      initial={{ opacity: 0, x: isUser ? -20 : 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div
        className={`
          max-w-[95%] rounded-2xl px-5 py-4 shadow-md
          ${isUser
            ? 'border border-[rgba(179,135,40,0.14)] text-[#2E3A56] shadow-[0_1px_2px_rgba(139,90,43,0.06),0_6px_24px_rgba(46,58,86,0.06),0_10px_36px_rgba(179,135,40,0.08)]'
            : 'bg-white/90 backdrop-blur-sm text-neutral-950 border-s-4 border-accent shadow-glass'
          }
        `}
        style={isUser ? { background: '#FCF7F0' } : undefined}
      >
        <div className={`prose prose-sm max-w-none ${isUser ? '' : 'text-neutral-950'}`}>
          <ReactMarkdown
            components={{
              p: ({ children }) => {
                const toArray = Array.isArray(children) ? children : (children != null ? [children] : []);
                const safe = toArray.filter((c: unknown) => c != null && String(c) !== 'undefined');
                return <p className="mb-2 last:mb-0 leading-relaxed">{safe.length ? safe : null}</p>;
              },
              ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
              li: ({ children }) => <li className="mb-1">{children}</li>,
              strong: ({ children }) => (
                <strong className={isUser ? 'text-[#24324A] font-bold' : 'text-[#0a0a0a] font-bold'}>{children}</strong>
              ),
              a: ({ href, children }) => (
                <a
                  href={href}
                  onClick={(e) => { if (href?.startsWith('/')) { e.preventDefault(); window.location.href = href; } }}
                  className={isUser ? 'text-[#2563eb] underline' : 'text-accent underline'}
                  style={{ fontWeight: 500, cursor: 'pointer' }}
                >
                  {children}
                </a>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        <div className={`text-xs mt-2 ${isUser ? 'text-[#5A6B8A]/70' : 'text-[#0D0D0D]/42'}`}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </motion.div>
  );
};
