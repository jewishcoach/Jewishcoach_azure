import { useEffect, useRef } from 'react';

interface RoleMessage {
  role: string;
}

/**
 * After new content: if the latest message is from the assistant, scroll so its **top**
 * is visible (readable start). Otherwise (user message / typing) keep anchoring to the bottom.
 *
 * When `stationGateActive`, anchor to the **bottom** of the transcript so the last coach bubble
 * stays fully readable above the tall station card + composer (avoids the card visually swallowing it).
 */
export function useChatScrollIntoLatest<T extends RoleMessage>(
  messages: T[],
  loading: boolean,
  stationGateActive = false,
  /** Extra scroll trigger (e.g. staggered welcome partial text). */
  scrollExtra: unknown = null,
) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastMessageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const scroll = () => {
      if (loading) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
        return;
      }
      if (stationGateActive) {
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
  }, [messages, loading, stationGateActive, scrollExtra]);

  return { messagesEndRef, lastMessageRef };
}
