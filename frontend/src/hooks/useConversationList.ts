import { useEffect, useMemo, useState } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ApiException } from '@/lib/api';
import {
  getConversations,
  type ConversationListItemResponse,
} from '@/lib/chat';

type PaginationState = {
  limit: number;
  offset: number;
  total: number;
};

export function useConversationList(initialLimit = 10) {
  const [pagination, setPagination] = useState<PaginationState>({
    limit: initialLimit,
    offset: 0,
    total: 0,
  });

  const query = useInfiniteQuery({
    queryKey: ['conversations'],
    queryFn: ({ pageParam, signal }) =>
      getConversations(pagination.limit, pageParam, signal),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const nextOffset =
        lastPage.pagination.offset + lastPage.conversations.length;
      return nextOffset < lastPage.pagination.total ? nextOffset : undefined;
    },
  });

  const conversations = useMemo<ConversationListItemResponse[]>(
    () => query.data?.pages.flatMap((page) => page.conversations) ?? [],
    [query.data],
  );

  useEffect(() => {
    if (!query.data || query.data.pages.length === 0) return;

    const firstPage = query.data.pages[0];
    const lastPage = query.data.pages[query.data.pages.length - 1];

    setPagination((current) => ({
      ...current,
      total: firstPage.pagination.total,
      offset: lastPage.pagination.offset + lastPage.conversations.length,
    }));
  }, [query.data]);

  const error = query.error instanceof ApiException ? query.error : null;

  useEffect(() => {
    if (!error) return;

    if (error.isRateLimit || error.status === 429) {
      toast.error('Muitas requisições. Aguarde alguns segundos.');
      return;
    }

    toast.error(error.message);
  }, [error]);

  const isLoading = query.isPending && conversations.length === 0;

  const fetchNextPage = async () => {
    if (!query.hasNextPage || query.isFetchingNextPage) return;
    await query.fetchNextPage();
  };

  const refetch = async () => {
    await query.refetch();
  };

  return {
    conversations,
    pagination,
    isLoading,
    isFetchingNextPage: query.isFetchingNextPage,
    error,
    refetch,
    hasNextPage: !!query.hasNextPage,
    fetchNextPage,
  };
}
