import { useEffect } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { MessageList } from '@/components/chat/MessageList';
import { ChatInput } from '@/components/chat/ChatInput';
import { useChat } from '@/hooks/useChat';
import { useChatStore } from '@/store/chatStore';

function parseConversationId(raw: string | undefined): number | null {
  if (!raw) return null;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}

export default function ChatPage() {
  const { id: rawId } = useParams<{ id?: string }>();
  const conversationId = parseConversationId(rawId);
  const navigate = useNavigate();
  const lastConversationId = useChatStore((s) => s.lastConversationId);
  const setLast = useChatStore((s) => s.setLast);
  const clearLast = useChatStore((s) => s.clear);
  const {
    messages,
    isLoading,
    error,
    send,
    retry,
    isSending,
    secondsLeft,
    isLocked,
  } = useChat(conversationId);

  useEffect(() => {
    if (!error) return;
    if (error.status === 404 || error.status === 403) {
      clearLast();
      toast.error('Conversa não encontrada.');
      navigate('/chat', { replace: true });
      return;
    }
    toast.error(error.message);
  }, [error, navigate, clearLast]);

  useEffect(() => {
    if (conversationId != null && !isLoading && !error) {
      setLast(conversationId);
    }
  }, [conversationId, isLoading, error, setLast]);

  if (conversationId == null && lastConversationId != null) {
    return <Navigate to={`/chat/${lastConversationId}`} replace />;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1">
        <MessageList
          messages={messages}
          isLoading={isLoading}
          isSending={isSending}
          isLocked={isLocked}
          onRetry={retry}
        />
      </div>
      <ChatInput
        onSubmit={send}
        disabled={isSending || isLocked}
        secondsLeft={secondsLeft}
      />
    </div>
  );
}
