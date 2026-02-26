import { useState, useEffect } from 'react';
import type { Message } from '../../types';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';
import { stripUndefined } from '../../utils/messageContent';

const TYPING_MS_PER_WORD = 28;

interface Props {
  message: Message;
  animateTyping?: boolean;
}

export const WorkspaceMessageBubble = ({ message, animateTyping = false }: Props) => {
  const isUser = message.role === 'user';
  const fullContent = stripUndefined(message.content ?? '');
  const [displayedContent, setDisplayedContent] = useState(
    animateTyping ? '' : fullContent
  );

  useEffect(() => {
    if (!animateTyping || !fullContent) return;
    const words = fullContent.split(/(\s+)/);
    let i = 0;
    const next = () => {
      if (i >= words.length) return;
      setDisplayedContent((prev) => prev + words[i]);
      i++;
      if (i < words.length) setTimeout(next, TYPING_MS_PER_WORD);
    };
    const t = setTimeout(next, 50);
    return () => clearTimeout(t);
  }, [animateTyping, fullContent]);

  const contentToRender = animateTyping ? displayedContent : fullContent;

  return (
    <motion.div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div
        className={`
          max-w-[85%] rounded-xl px-9 py-6 shadow-sm
          ${isUser ? '' : ''}
        `}
        style={{
          background: isUser ? 'rgba(46, 58, 86, 0.08)' : '#FFFFFF',
          border: isUser ? '1px solid rgba(46, 58, 86, 0.15)' : '1px solid #E2E4E8',
          ...(isUser && { borderRight: '3px solid rgba(179, 135, 40, 0.5)' }),
        }}
      >
        <div className={`prose prose-sm max-w-none ${isUser ? '' : ''}`} dir="rtl" style={{ fontFamily: 'Inter, sans-serif', fontWeight: 300, lineHeight: 1.6, color: isUser ? '#2E3A56' : '#2E3A56', textAlign: 'justify' }}>
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-4 last:mb-0 leading-relaxed text-[16px]" style={{ lineHeight: 1.7, textAlign: 'justify' }}>{children}</p>,
              ul: ({ children }) => <ul className="list-disc list-inside mb-4 space-y-2 text-[16px]" style={{ lineHeight: 1.7 }}>{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside mb-4 space-y-2 text-[16px]" style={{ lineHeight: 1.7 }}>{children}</ol>,
              li: ({ children }) => <li className="mb-1">{children}</li>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
            }}
          >
            {contentToRender}
          </ReactMarkdown>
        </div>
        <div className={`text-[11px] mt-2 ${isUser ? 'text-[#5A6B8A]/70' : 'text-[#5A6B8A]/60'}`}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </motion.div>
  );
};
