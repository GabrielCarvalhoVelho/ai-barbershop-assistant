import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationList } from './ConversationList';
import { useConversationList } from '@/hooks/useConversationList';
import { ApiException } from '@/lib/api';

const navigateMock = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom',
  );

  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('@/hooks/useConversationList', () => ({
  useConversationList: vi.fn(),
}));

type ConversationListHookState = ReturnType<typeof useConversationList>;

const mockedUseConversationList = vi.mocked(useConversationList);

function buildHookState(
  partial: Partial<ConversationListHookState> = {},
): ConversationListHookState {
  return {
    conversations: [],
    pagination: { limit: 10, offset: 0, total: 0 },
    isLoading: false,
    isFetchingNextPage: false,
    error: null,
    refetch: vi.fn().mockResolvedValue(undefined),
    hasNextPage: false,
    fetchNextPage: vi.fn().mockResolvedValue(undefined),
    ...partial,
  };
}

describe('ConversationList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedUseConversationList.mockReturnValue(buildHookState());
  });

  it('renderiza empty state quando não há conversas', () => {
    render(<ConversationList />);

    expect(screen.getByText('Nenhuma conversa encontrada.')).toBeTruthy();
  });

  it('renderiza lista de conversas com dados principais', () => {
    mockedUseConversationList.mockReturnValue(
      buildHookState({
        conversations: [
          {
            id: 12,
            status: 'active',
            started_at: '2026-05-09T12:00:00Z',
            ended_at: null,
            message_count: 3,
            last_message_preview: 'Quero agendar para amanhã',
          },
        ],
        pagination: { limit: 10, offset: 0, total: 1 },
      }),
    );

    render(<ConversationList />);

    expect(screen.getByText('#12')).toBeTruthy();
    expect(screen.getByText('Ativa')).toBeTruthy();
    expect(screen.getByText('3 mensagens')).toBeTruthy();
    expect(screen.getByText('Quero agendar para amanhã')).toBeTruthy();
  });

  it('renderiza skeleton durante carregamento inicial', () => {
    mockedUseConversationList.mockReturnValue(
      buildHookState({
        isLoading: true,
      }),
    );

    render(<ConversationList />);

    expect(screen.getByLabelText('Carregando conversas')).toBeTruthy();
  });

  it('renderiza estado de erro e chama retry', async () => {
    const user = userEvent.setup();
    const refetch = vi.fn().mockResolvedValue(undefined);

    mockedUseConversationList.mockReturnValue(
      buildHookState({
        error: new ApiException(
          'APP_000',
          'Falha temporária',
          500,
          null,
          null,
          null,
        ),
        refetch,
      }),
    );

    render(<ConversationList />);

    await user.click(screen.getByRole('button', { name: 'Tentar novamente' }));

    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it('redireciona ao clicar em conversa quando não recebe callback', async () => {
    const user = userEvent.setup();

    mockedUseConversationList.mockReturnValue(
      buildHookState({
        conversations: [
          {
            id: 5,
            status: 'closed',
            started_at: '2026-05-09T12:00:00Z',
            ended_at: '2026-05-09T12:10:00Z',
            message_count: 2,
            last_message_preview: null,
          },
        ],
        pagination: { limit: 10, offset: 0, total: 1 },
      }),
    );

    render(<ConversationList />);

    await user.click(screen.getByRole('button', { name: 'Abrir conversa 5' }));

    expect(navigateMock).toHaveBeenCalledWith('/chat/5');
  });

  it('usa callback onSelectConversation quando informado', async () => {
    const user = userEvent.setup();
    const onSelectConversation = vi.fn();

    mockedUseConversationList.mockReturnValue(
      buildHookState({
        conversations: [
          {
            id: 7,
            status: 'active',
            started_at: '2026-05-09T12:00:00Z',
            ended_at: null,
            message_count: 1,
            last_message_preview: 'Olá',
          },
        ],
        pagination: { limit: 10, offset: 0, total: 1 },
      }),
    );

    render(<ConversationList onSelectConversation={onSelectConversation} />);

    await user.click(screen.getByRole('button', { name: 'Abrir conversa 7' }));

    expect(onSelectConversation).toHaveBeenCalledWith(7);
    expect(navigateMock).not.toHaveBeenCalled();
  });
});
