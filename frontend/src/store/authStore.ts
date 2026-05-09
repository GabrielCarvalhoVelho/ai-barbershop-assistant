import { create } from 'zustand';
import type { UserMeResponse } from '@/types/api';

type AuthState = {
  user: UserMeResponse | null;
  setUser: (user: UserMeResponse | null) => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
}));
