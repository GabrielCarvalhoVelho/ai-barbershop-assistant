import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from 'next-themes';
import { AppShell } from '@/components/layout/AppShell';
import ChatPage from './ChatPage';
import { useChatStore } from '@/store/chatStore';

const useAuthMock = vi.fn();
const useConversationListMock = vi.fn();
const useChatMock = vi.fn();

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock('@/hooks/useConversationList', () => ({
  useConversationList: () => useConversationListMock(),
}));

vi.mock('@/hooks/useChat', () => ({
  useChat: (conversationId: number | null) => useChatMock(conversationId),
}));

function renderFlow(initialEntry = '/chat') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/chat/:id" element={<ChatPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

describe('Chat Flow Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useChatStore.getState().clear();

    useAuthMock.mockReturnValue({
      user: {
        id: 1,
        name: 'Cliente Teste',
        email: null,
        phone: '+5511999999999',
        role: 'customer',
        company_id: 1,
      },
      isAuthenticated: true,
      isHydrating: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
    });

    useConversationListMock.mockReturnValue({
      conversations: [
        {
          id: 10,
          status: 'active',
          started_at: '2026-05-10T12:00:00Z',
          ended_at: null,
          message_count: 2,
          last_message_preview: 'Quero agendar para amanha',
        },
      ],
      pagination: { limit: 10, offset: 0, total: 1 },
      isLoading: false,
      isFetchingNextPage: false,
      error: null,
      refetch: vi.fn().mockResolvedValue(undefined),
      hasNextPage: false,
      fetchNextPage: vi.fn().mockResolvedValue(undefined),
    });

    useChatMock.mockImplementation((conversationId: number | null) => {
      if (conversationId === 10) {
        return {
          messages: [
            {
              id: 1,
              sender: 'user',
              content: 'Quero agendar para amanha',
              created_at: '2026-05-10T12:00:10Z',
            },
            {
              id: 2,
              sender: 'bot',
              content: 'Perfeito, qual horario voce prefere?',
              created_at: '2026-05-10T12:00:11Z',
            },
          ],
          isLoading: false,
          error: null,
          send: vi.fn(),
          retry: vi.fn(),
          isSending: false,
          secondsLeft: 0,
          isLocked: false,
        };
      }

      return {
        messages: [],
        isLoading: false,
        error: null,
        send: vi.fn(),
        retry: vi.fn(),
        isSending: false,
        secondsLeft: 0,
        isLocked: false,
      };
    });
  });

  it('navega da sidebar para a conversa e renderiza historico', async () => {
    const user = userEvent.setup();
    renderFlow('/chat');

    expect(screen.getByText('Comece a conversar com a barbearia.')).toBeTruthy();

    await user.click(screen.getByRole('button', { name: 'Abrir conversa 10' }));

    await waitFor(() => {
      expect(screen.getAllByText('Quero agendar para amanha').length).toBe(2);
      expect(
        screen.getByText('Perfeito, qual horario voce prefere?'),
      ).toBeTruthy();
    });

    expect(useChatMock).toHaveBeenCalledWith(null);
    expect(useChatMock).toHaveBeenCalledWith(10);
  });
});
