import { create } from "zustand";

export interface ChatMessage {
  id: string;
  role: "user" | "kairos";
  text: string;
  pending?: boolean;
}

interface ChatState {
  messages: ChatMessage[];
  loading: boolean;
  panelOpen: boolean;
  addMessage: (m: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  setLoading: (b: boolean) => void;
  setPanelOpen: (b: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  loading: false,
  panelOpen: false,
  addMessage: (m) =>
    set((s) => ({ messages: [...s.messages, m], panelOpen: true })),
  updateMessage: (id, patch) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    })),
  setLoading: (loading) => set({ loading }),
  setPanelOpen: (panelOpen) => set({ panelOpen }),
}));
