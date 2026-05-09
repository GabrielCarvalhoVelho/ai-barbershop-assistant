import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type ChatState = {
  lastConversationId: number | null;
  setLast: (id: number | null) => void;
  clear: () => void;
};

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      lastConversationId: null,
      setLast: (id) => set({ lastConversationId: id }),
      clear: () => set({ lastConversationId: null }),
    }),
    { name: 'bb_chat' },
  ),
);
