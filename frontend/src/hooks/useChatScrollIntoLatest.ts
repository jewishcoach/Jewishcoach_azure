import { useEffect, useRef } from 'react';

interface RoleMessage {
  role: string;
}

/**
 * After new content: if the latest message is from the assistant, scroll so its **top**
 * is visible (readable start). Otherwise (user message / typing) keep anchoring to the bottom.
 */
export function useChatScrollIntoLatest<T extends RoleMessage>(messages: T[], loading: boolean) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastMessageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const scroll = () => {
      if (loading) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
        return;
      }
      const last = messages[messages.length - 1];
      if (last?.role === 'assistant') {
        lastMessageRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }
    };
    requestAnimationFrame(() => requestAnimationFrame(scroll));
  }, [messages, loading]);

  return { messagesEndRef, lastMessageRef };
}
