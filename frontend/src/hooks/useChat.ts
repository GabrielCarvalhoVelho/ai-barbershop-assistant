import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { getMessages, sendMessage } from '@/lib/chat';
import { ApiException } from '@/lib/api';
import type { ConversationMessages, Message } from '@/types/api';

export const messagesQueryKey = (id: number) => ['messages', id] as const;
const PENDING_KEY = ['messages', 'pending'] as const;
const LOCKOUT_MS = 6000;

type SendContext = { key: readonly unknown[] };

export function useChat(conversationId: number | null) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const effectiveKey =
    conversationId != null ? messagesQueryKey(conversationId) : PENDING_KEY;

  const query = useQuery({
    queryKey: effectiveKey,
    queryFn: ({ signal }) =>
      getMessages(conversationId as number, { limit: 50 }, signal),
    enabled: conversationId != null,
  });

  const [lockedUntil, setLockedUntil] = useState<number | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);

  useEffect(() => {
    if (lockedUntil == null) {
      setSecondsLeft(0);
      return;
    }
    const update = () => {
      const ms = lockedUntil - Date.now();
      if (ms <= 0) {
        setLockedUntil(null);
        setSecondsLeft(0);
      } else {
        setSecondsLeft(Math.ceil(ms / 1000));
      }
    };
    update();
    const handle = setInterval(update, 250);
    return () => clearInterval(handle);
  }, [lockedUntil]);

  const messages: Message[] = query.data?.messages ?? [];
  const isLoading =
    conversationId != null &&
    query.isPending &&
    query.fetchStatus !== 'idle';
  const error = query.error as ApiException | null;

  const mutation = useMutation<
    Awaited<ReturnType<typeof sendMessage>>,
    unknown,
    string,
    SendContext
  >({
    mutationFn: (text) =>
      sendMessage({ message: text, conversation_id: conversationId }),

    onMutate: async (text) => {
      const key = effectiveKey;
      await queryClient.cancelQueries({ queryKey: key });
      const optimistic: Message = {
        id: -Date.now(),
        sender: 'user',
        content: text,
        created_at: new Date().toISOString(),
      };
      queryClient.setQueryData<ConversationMessages>(key, (old) => {
        if (!old) {
          return {
            conversation_id: conversationId ?? 0,
            messages: [optimistic],
            pagination: { limit: 50, offset: 0, total: 1 },
          };
        }
        return { ...old, messages: [...old.messages, optimistic] };
      });
      return { key };
    },

    onSuccess: (response) => {
      const botMsg: Message = {
        id: -Date.now(),
        sender: 'bot',
        content: response.response,
        created_at: new Date().toISOString(),
      };
      const targetKey = messagesQueryKey(response.conversation_id);

      if (conversationId == null) {
        const pending =
          queryClient.getQueryData<ConversationMessages>(PENDING_KEY);
        const pendingMsgs = pending?.messages ?? [];
        queryClient.setQueryData<ConversationMessages>(targetKey, {
          conversation_id: response.conversation_id,
          messages: [...pendingMsgs, botMsg],
          pagination: {
            limit: 50,
            offset: 0,
            total: pendingMsgs.length + 1,
          },
        });
        queryClient.removeQueries({ queryKey: PENDING_KEY });
        navigate(`/chat/${response.conversation_id}`, { replace: true });
      } else {
        queryClient.setQueryData<ConversationMessages>(targetKey, (old) => {
          if (!old) return old;
          return { ...old, messages: [...old.messages, botMsg] };
        });
      }
    },

    onError: (err, _text, ctx) => {
      if (ctx?.key) {
        queryClient.setQueryData<ConversationMessages>(ctx.key, (old) => {
          if (!old || old.messages.length === 0) return old;
          const msgs = old.messages.slice();
          const lastIdx = msgs.length - 1;
          if (msgs[lastIdx].sender === 'user') {
            msgs[lastIdx] = { ...msgs[lastIdx], failed: true };
          }
          return { ...old, messages: msgs };
        });
      }

      if (err instanceof ApiException) {
        if (err.isRateLimit) {
          setLockedUntil(Date.now() + LOCKOUT_MS);
          toast.error('Muitas mensagens. Aguarde alguns segundos.');
        } else if (err.code === 'CHAT_001') {
          toast.error(err.message);
        } else if (err.isNetworkError) {
          toast.error('Sem conexão. Tente novamente.');
        } else {
          toast.error(err.message);
        }
      } else {
        toast.error('Erro ao enviar.');
      }
    },
  });

  const isLocked = secondsLeft > 0;

  const send = (text: string) => {
    if (isLocked) return;
    mutation.mutate(text);
  };

  const retry = (msg: Message) => {
    if (!msg.failed || isLocked) return;
    queryClient.setQueryData<ConversationMessages>(effectiveKey, (old) => {
      if (!old) return old;
      return {
        ...old,
        messages: old.messages.filter((m) => m.id !== msg.id),
      };
    });
    mutation.mutate(msg.content);
  };

  return {
    messages,
    isLoading,
    error,
    send,
    retry,
    isSending: mutation.isPending,
    secondsLeft,
    isLocked,
  };
}
