import { useState, useEffect } from 'react';
import type { Message } from '../../types';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';
import { stripUndefined } from '../../utils/messageContent';
import { WORKSPACE_CHAT_FONT } from '../../constants/workspaceFonts';

const TYPING_MS_PER_WORD = 28;

interface Props {
  message: Message;
  animateTyping?: boolean;
  dir?: 'ltr' | 'rtl';
}

export const WorkspaceMessageBubble = ({ message, animateTyping = false, dir = 'rtl' }: Props) => {
  const isUser = message.role === 'user';
  const fullContent = stripUndefined(message.content ?? '');
  const [displayedContent, setDisplayedContent] = useState(
    animateTyping ? '' : fullContent
  );

  useEffect(() => {
    if (!animateTyping) {
      setDisplayedContent(fullContent);
      return;
    }
    if (!fullContent) {
      setDisplayedContent('');
      return;
    }
    let cancelled = false;
    let pending: ReturnType<typeof setTimeout> | null = null;
    const words = fullContent.split(/(\s+)/);
    let i = 0;
    setDisplayedContent('');
    const step = () => {
      if (cancelled) return;
      if (i >= words.length) return;
      setDisplayedContent((prev) => prev + words[i]);
      i++;
      if (i < words.length) {
        pending = setTimeout(step, TYPING_MS_PER_WORD);
      }
    };
    pending = setTimeout(step, 50);
    return () => {
      cancelled = true;
      if (pending != null) clearTimeout(pending);
    };
  }, [animateTyping, fullContent]);

  /**
   * Feeding growing Hebrew (or mixed) text into ReactMarkdown breaks the parser (merged words,
   * stray "undefined"). During typing, render plain text; run Markdown only on the final string.
   */
  const showPlainTyping = animateTyping && displayedContent !== fullContent;
  const contentToRender = showPlainTyping ? displayedContent : fullContent;

  return (
    <motion.div
      className={`flex ${isUser ? 'justify-start' : 'justify-end'}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div
        className="max-w-[90%] md:max-w-[85%] rounded-2xl px-5 py-4 md:px-9 md:py-6"
        style={{
          background: isUser ? '#FCF7F0' : '#FFFFFF',
          border: isUser ? '1px solid rgba(179, 135, 40, 0.14)' : 'none',
          boxShadow: isUser
            ? '0 1px 2px rgba(139, 90, 43, 0.06), 0 6px 24px rgba(46, 58, 86, 0.06), 0 10px 36px rgba(179, 135, 40, 0.08)'
            : '0 1px 2px rgba(15, 23, 42, 0.035), 0 6px 22px rgba(46, 58, 86, 0.05)',
        }}
      >
        <div
          className={`prose prose-sm max-w-none ${isUser ? '' : ''}`}
          dir={dir}
          style={{
            fontFamily: WORKSPACE_CHAT_FONT,
            fontWeight: 400,
            lineHeight: 1.6,
            color: isUser ? '#2E3A56' : '#0D0D0D',
            textAlign: dir === 'rtl' ? 'justify' : 'left',
            direction: dir,
            unicodeBidi: 'isolate',
          }}
        >
          {showPlainTyping ? (
            <div
              className="whitespace-pre-wrap break-words leading-relaxed text-[14px] md:text-[16px]"
              style={{ lineHeight: 1.65, textAlign: dir === 'rtl' ? 'justify' : 'left' }}
            >
              {displayedContent}
            </div>
          ) : (
            <ReactMarkdown
              components={{
                p: ({ children }) => {
                  const safe = Array.isArray(children) ? children.filter((c: unknown) => c != null && String(c) !== 'undefined') : (children != null ? [children] : []);
                  return <p className="mb-3 md:mb-4 last:mb-0 leading-relaxed text-[14px] md:text-[16px]" style={{ lineHeight: 1.65, textAlign: dir === 'rtl' ? 'justify' : 'left' }}>{safe.length ? safe : null}</p>;
                },
                ul: ({ children }) => <ul className="list-disc list-inside mb-3 md:mb-4 space-y-1 md:space-y-2 text-[14px] md:text-[16px]" style={{ lineHeight: 1.65 }}>{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside mb-3 md:mb-4 space-y-1 md:space-y-2 text-[14px] md:text-[16px]" style={{ lineHeight: 1.65 }}>{children}</ol>,
                li: ({ children }) => <li className="mb-1">{children}</li>,
                strong: ({ children }) => (
                  <strong className={`font-semibold ${isUser ? '' : 'text-[#0a0a0a]'}`}>{children}</strong>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    onClick={(e) => { if (href?.startsWith('/')) { e.preventDefault(); window.location.href = href; } }}
                    style={{ color: '#B38728', textDecoration: 'underline', fontWeight: 500, cursor: 'pointer' }}
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {contentToRender}
            </ReactMarkdown>
          )}
        </div>
        <div className={`text-[11px] mt-2 ${isUser ? 'text-[#5A6B8A]/70' : 'text-[#0D0D0D]/42'}`}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </motion.div>
  );
};
