import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';

export default function ChatPage() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="flex items-center justify-between border-b border-border bg-card px-6 py-4">
        <div>
          <p className="text-sm text-muted-foreground">Logado como</p>
          <p className="text-base font-medium">
            {user.name}{' '}
            <span className="text-xs text-muted-foreground">({user.role})</span>
          </p>
        </div>
        <Button variant="outline" onClick={logout}>
          Sair
        </Button>
      </header>
      <main className="flex flex-1 items-center justify-center text-muted-foreground">
        Chat em breve.
      </main>
    </div>
  );
}
