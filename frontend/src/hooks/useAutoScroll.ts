import { useCallback, useEffect, useRef, useState } from 'react';
import type { Message } from '@/types/api';

const BOTTOM_THRESHOLD_PX = 64;

export function useAutoScroll(messages: Message[], isSending?: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [hasNewBelow, setHasNewBelow] = useState(false);
  const lastIdRef = useRef<number | null>(null);
  const isFirstRef = useRef(true);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    const atBottom = distance < BOTTOM_THRESHOLD_PX;
    setIsAtBottom(atBottom);
    if (atBottom) setHasNewBelow(false);
  }, []);

  useEffect(() => {
    const last = messages[messages.length - 1];
    const lastId = last?.id ?? null;

    if (lastId === lastIdRef.current) return;

    const previousId = lastIdRef.current;
    lastIdRef.current = lastId;

    if (!last) return;

    const isFirst = isFirstRef.current;
    isFirstRef.current = false;

    const userJustSent = last.sender === 'user' && previousId !== null;
    const shouldScroll = isFirst || userJustSent || isAtBottom;

    if (shouldScroll) {
      endRef.current?.scrollIntoView({
        block: 'end',
        behavior: isFirst ? 'instant' : 'smooth',
      });
      setHasNewBelow(false);
    } else {
      setHasNewBelow(true);
    }
  }, [messages, isAtBottom]);

  useEffect(() => {
    if (isSending && isAtBottom) {
      endRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' });
    }
  }, [isSending, isAtBottom]);

  const scrollToBottom = useCallback(() => {
    endRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' });
    setHasNewBelow(false);
  }, []);

  return {
    containerRef,
    endRef,
    handleScroll,
    scrollToBottom,
    hasNewBelow,
  };
}
