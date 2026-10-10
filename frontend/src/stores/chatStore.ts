import { create } from "zustand";
import type { AnalysisResult } from "../types/analysis";

export interface ChatMessage {
  id: string;
  role: "user" | "kairos";
  text: string;
  pending?: boolean;
  error?: boolean;
  reasoning?: string;
  results?: AnalysisResult[];
}

interface ChatState {
  messages: ChatMessage[];
  loading: boolean;
  panelOpen: boolean;
  addMessage: (m: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  setLoading: (b: boolean) => void;
  setPanelOpen: (b: boolean) => void;
  clear: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  loading: false,
  panelOpen: false,
  addMessage: (m) => set((s) => ({ messages: [...s.messages, m], panelOpen: true })),
  updateMessage: (id, patch) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    })),
  setLoading: (loading) => set({ loading }),
  setPanelOpen: (panelOpen) => set({ panelOpen }),
  clear: () => set({ messages: [], panelOpen: false }),
}));
