import { useNavigate } from 'react-router-dom';
import { Loader2, MessageSquare, RefreshCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useConversationList } from '@/hooks/useConversationList';
import type { ConversationListItemResponse } from '@/lib/chat';

type ConversationListProps = {
  onSelectConversation?: (id: number) => void;
  maxHeight?: string;
};

function formatStartedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date);
}

function statusLabel(status: ConversationListItemResponse['status']) {
  return status === 'active' ? 'Ativa' : 'Encerrada';
}

function statusClass(status: ConversationListItemResponse['status']) {
  return status === 'active'
    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
    : 'border-zinc-500/30 bg-zinc-500/10 text-zinc-700 dark:text-zinc-300';
}

function SkeletonItem() {
  return (
    <div className="rounded-md border border-border p-3" aria-hidden="true">
      <div className="mb-2 h-3 w-28 animate-pulse rounded bg-muted" />
      <div className="mb-2 h-3 w-16 animate-pulse rounded bg-muted" />
      <div className="h-3 w-full animate-pulse rounded bg-muted" />
    </div>
  );
}

export function ConversationList({
  onSelectConversation,
  maxHeight = '100%',
}: ConversationListProps) {
  const navigate = useNavigate();
  const {
    conversations,
    pagination,
    isLoading,
    isFetchingNextPage,
    error,
    refetch,
    hasNextPage,
    fetchNextPage,
  } = useConversationList();

  const handleSelect = (id: number) => {
    if (onSelectConversation) {
      onSelectConversation(id);
      return;
    }
    navigate(`/chat/${id}`);
  };

  if (isLoading) {
    return (
      <div className="space-y-2" aria-label="Carregando conversas">
        <SkeletonItem />
        <SkeletonItem />
        <SkeletonItem />
      </div>
    );
  }

  if (error && conversations.length === 0) {
    return (
      <div className="rounded-md border border-border p-3 text-sm">
        <p className="text-muted-foreground">Erro ao carregar conversas.</p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void refetch()}
          className="mt-3 gap-2"
        >
          <RefreshCcw className="h-4 w-4" />
          Tentar novamente
        </Button>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">
        Nenhuma conversa encontrada.
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-col" style={{ maxHeight }}>
      <div className="flex-1 space-y-2 overflow-y-auto pr-1">
        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            type="button"
            onClick={() => handleSelect(conversation.id)}
            className="w-full rounded-md border border-border p-3 text-left transition-colors hover:bg-accent/60"
            aria-label={`Abrir conversa ${conversation.id}`}
          >
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-sm font-medium">#{conversation.id}</span>
              <span
                className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${statusClass(conversation.status)}`}
              >
                {statusLabel(conversation.status)}
              </span>
            </div>
            <p className="mb-1 text-xs text-muted-foreground">
              Iniciada em {formatStartedAt(conversation.started_at)}
            </p>
            <p className="mb-2 flex items-center gap-1 text-xs text-muted-foreground">
              <MessageSquare className="h-3.5 w-3.5" />
              {conversation.message_count} mensagens
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {conversation.last_message_preview ?? 'Sem mensagens recentes.'}
            </p>
          </button>
        ))}
      </div>

      {hasNextPage && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="mt-2"
          onClick={() => void fetchNextPage()}
          disabled={isFetchingNextPage}
        >
          {isFetchingNextPage ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Carregando...
            </>
          ) : (
            'Carregar mais'
          )}
        </Button>
      )}

      <p className="mt-2 text-xs text-muted-foreground">
        {conversations.length} de {pagination.total} conversas
      </p>
    </div>
  );
}
