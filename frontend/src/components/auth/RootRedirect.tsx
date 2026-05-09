import { Navigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { getToken } from '@/lib/token';

export function RootRedirect() {
  const { isAuthenticated, isHydrating } = useAuth();
  const hasToken = !!getToken();

  if (!hasToken) return <Navigate to="/login" replace />;
  if (isHydrating) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (isAuthenticated) return <Navigate to="/chat" replace />;
  return <Navigate to="/login" replace />;
}
