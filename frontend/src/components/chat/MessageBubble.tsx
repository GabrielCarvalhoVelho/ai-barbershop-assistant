import { AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Message } from '@/types/api';

type Props = {
  message: Message;
  onRetry?: (msg: Message) => void;
  disabledRetry?: boolean;
};

export function MessageBubble({ message, onRetry, disabledRetry }: Props) {
  const isUser = message.sender === 'user';
  const failed = message.failed === true;

  return (
    <div
      className={cn(
        'flex w-full flex-col gap-1',
        isUser ? 'items-end' : 'items-start',
      )}
    >
      <div
        className={cn(
          'max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap break-words md:max-w-[70%]',
          isUser
            ? failed
              ? 'border border-destructive bg-destructive/10 text-destructive'
              : 'bg-primary text-primary-foreground'
            : 'bg-muted text-foreground',
        )}
      >
        {message.content}
      </div>
      {failed && (
        <button
          type="button"
          onClick={() => onRetry?.(message)}
          disabled={disabledRetry}
          className="flex items-center gap-1 text-xs text-destructive hover:underline disabled:cursor-not-allowed disabled:opacity-50 disabled:no-underline"
        >
          <AlertCircle className="h-3 w-3" />
          Tentar novamente
        </button>
      )}
    </div>
  );
}
