import { ChevronDown } from 'lucide-react';

type Props = { onClick: () => void };

export function NewMessagePill({ onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium shadow-md hover:bg-accent animate-in fade-in slide-in-from-bottom-2 duration-200"
    >
      <ChevronDown className="h-3.5 w-3.5" />
      Nova mensagem
    </button>
  );
}
