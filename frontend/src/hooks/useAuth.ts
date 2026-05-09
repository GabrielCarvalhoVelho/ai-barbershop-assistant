import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import {
  login as loginApi,
  register as registerApi,
  me as meApi,
} from '@/lib/auth';
import { clearToken, getToken, setToken } from '@/lib/token';
import type { LoginRequest, RegisterRequest } from '@/types/api';

export function useAuth() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const meQuery = useQuery({
    queryKey: ['me'],
    queryFn: ({ signal }) => meApi(signal),
    enabled: !!getToken() && !user,
    staleTime: Infinity,
    retry: false,
  });

  useEffect(() => {
    if (meQuery.data) setUser(meQuery.data);
  }, [meQuery.data, setUser]);

  const login = async (creds: LoginRequest) => {
    const tok = await loginApi(creds);
    setToken(tok.access_token);
    const u = await meApi();
    setUser(u);
    queryClient.setQueryData(['me'], u);
  };

  const register = async (data: RegisterRequest) => {
    const tok = await registerApi(data);
    setToken(tok.access_token);
    const u = await meApi();
    setUser(u);
    queryClient.setQueryData(['me'], u);
  };

  const logout = () => {
    clearToken();
    setUser(null);
    queryClient.clear();
    navigate('/login', { replace: true });
  };

  const hasToken = !!getToken();
  const isAuthenticated = !!user;
  const isHydrating =
    hasToken && !user && (meQuery.isPending || meQuery.isFetching);

  return { user, isAuthenticated, isHydrating, login, register, logout };
}
