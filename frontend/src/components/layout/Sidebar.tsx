import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { LogOut, Plus } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { useChatStore } from '@/store/chatStore';

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? '')
    .join('');
}

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const clearLast = useChatStore((s) => s.clear);

  const handleNewConversation = () => {
    clearLast();
    queryClient.removeQueries({ queryKey: ['messages', 'pending'] });
    navigate('/chat');
  };

  return (
    <div className="flex h-full flex-col p-4">
      <div className="mb-4">
        <p className="text-sm font-semibold">Barbearia AI</p>
      </div>

      <Button
        onClick={handleNewConversation}
        className="w-full justify-start gap-2"
      >
        <Plus className="h-4 w-4" />
        Nova conversa
      </Button>

      <div className="flex-1" />

      {user && (
        <div className="flex items-center gap-3 border-t border-border pt-3">
          <Avatar className="h-9 w-9">
            <AvatarFallback>{initials(user.name)}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{user.name}</p>
            <p className="truncate text-xs text-muted-foreground">{user.role}</p>
          </div>
          <Button
            onClick={logout}
            size="icon"
            variant="ghost"
            aria-label="Sair"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
