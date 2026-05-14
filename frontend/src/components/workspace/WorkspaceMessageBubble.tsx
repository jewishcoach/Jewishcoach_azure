import { useState, useEffect } from 'react';
import type { CSSProperties } from 'react';
import type { Message } from '../../types';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { stripUndefined } from '../../utils/messageContent';
import { emphasizeBsdCoachTerms } from '../../utils/emphasizeBsdCoachTerms';
import { WORKSPACE_CHAT_FONT } from '../../constants/workspaceFonts';

const TYPING_MS_PER_WORD = 28;

interface Props {
  message: Message;
  animateTyping?: boolean;
  dir?: 'ltr' | 'rtl';
}

export const WorkspaceMessageBubble = ({ message, animateTyping = false, dir = 'rtl' }: Props) => {
  const { t, i18n } = useTranslation();
  const isUser = message.role === 'user';
  /** Parent scroll region is dir=ltr; Hebrew chat keeps coach on the right, English mirrors typical LTR messengers (coach left). */
  const isHebrewChat = i18n.language.startsWith('he');
  const rowJustify = isHebrewChat === isUser ? 'justify-start' : 'justify-end';
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
  const rawContent = showPlainTyping ? displayedContent : fullContent;
  const contentToRender =
    !isUser && !showPlainTyping ? emphasizeBsdCoachTerms(fullContent, i18n.language) : rawContent;

  const bubbleChrome: CSSProperties = {
    background: '#FFFFFF',
    border: '1px solid #e8e0cc',
    boxShadow: '0px 1px 4px rgba(10, 10, 10, 0.06)',
    borderTopLeftRadius: 4,
    borderTopRightRadius: 18,
    borderBottomRightRadius: 18,
    borderBottomLeftRadius: 18,
  };

  const bubbleInner = (
    <div
      className={`px-5 py-4 md:px-5 md:py-5 ${isUser ? 'w-fit max-w-full' : 'w-full'}`}
      style={bubbleChrome}
    >
      <div
        className={`prose prose-sm max-w-none ${isUser ? '' : ''}`}
        dir={dir}
        style={{
          fontFamily: WORKSPACE_CHAT_FONT,
          fontWeight: 400,
          lineHeight: 1.65,
          color: '#1a1510',
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
                  <strong
                    className={`font-semibold ${isUser ? '' : 'text-[#7A5E16]'}`}
                    style={isUser ? undefined : { fontWeight: 650 }}
                  >
                    {children}
                  </strong>
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
      <div className="mt-3 flex justify-end text-[13px] font-light tabular-nums text-[#717171]">
        {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </div>
    </div>
  );

  const coachBadgeRow =
    !isUser ? (
      <div
        className={`mb-0 flex items-center gap-2 ${isHebrewChat ? 'flex-row-reverse' : ''}`}
      >
        <div
          className="flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-[11px] bg-[#ffb022] text-[10px] font-medium text-[#0e1117]"
          aria-hidden
        >
          B
        </div>
        <span
          className="text-[12px] font-light uppercase tracking-[1px] text-[#4c5a70]"
          style={{ fontFamily: WORKSPACE_CHAT_FONT }}
        >
          {t('chat.virtualCoachBadge')}
        </span>
      </div>
    ) : null;

  const stackAlign = isUser
    ? isHebrewChat
      ? 'items-start'
      : 'items-end'
    : isHebrewChat
      ? 'items-end'
      : 'items-start';

  return (
    <motion.div
      className={`flex ${rowJustify}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div
        className={`flex w-full max-w-[min(92%,600px)] flex-col gap-2 ${stackAlign}`}
      >
        {coachBadgeRow}
        {bubbleInner}
      </div>
    </motion.div>
  );
};
