import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type Props = {
  onSubmit: (text: string) => void;
  disabled?: boolean;
  secondsLeft?: number;
};

const MAX_HEIGHT = 120;

export function ChatInput({ onSubmit, disabled, secondsLeft }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [value]);

  const trimmed = value.trim();
  const canSend = trimmed.length > 0 && !disabled;
  const showCountdown = secondsLeft != null && secondsLeft > 0;

  const submit = () => {
    if (!canSend) return;
    onSubmit(trimmed);
    setValue('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleFormSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  return (
    <form
      onSubmit={handleFormSubmit}
      className="flex shrink-0 items-end gap-2 border-t border-border bg-card p-3"
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        placeholder="Digite sua mensagem..."
        disabled={disabled}
        className={cn(
          'flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm',
          'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
          'disabled:opacity-50',
        )}
        style={{ maxHeight: MAX_HEIGHT }}
      />
      <Button type="submit" size="icon" disabled={!canSend} aria-label="Enviar">
        {showCountdown ? (
          <span className="text-xs font-medium">{secondsLeft}s</span>
        ) : (
          <Send className="h-4 w-4" />
        )}
      </Button>
    </form>
  );
}
