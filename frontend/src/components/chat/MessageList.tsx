import { Loader2 } from 'lucide-react';
import type { Message } from '@/types/api';
import { useAutoScroll } from '@/hooks/useAutoScroll';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { NewMessagePill } from './NewMessagePill';

type Props = {
  messages: Message[];
  isLoading?: boolean;
  isSending?: boolean;
  isLocked?: boolean;
  onRetry?: (msg: Message) => void;
};

export function MessageList({
  messages,
  isLoading,
  isSending,
  isLocked,
  onRetry,
}: Props) {
  const { containerRef, endRef, handleScroll, scrollToBottom, hasNewBelow } =
    useAutoScroll(messages, isSending);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (messages.length === 0 && !isSending) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-center text-sm text-muted-foreground">
        Comece a conversar com a barbearia.
      </div>
    );
  }

  return (
    <div className="relative h-full">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex h-full flex-col gap-3 overflow-y-auto px-4 py-4"
      >
        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            message={m}
            onRetry={onRetry}
            disabledRetry={isLocked}
          />
        ))}
        {isSending && <TypingIndicator />}
        <div ref={endRef} />
      </div>
      {hasNewBelow && <NewMessagePill onClick={scrollToBottom} />}
    </div>
  );
}
