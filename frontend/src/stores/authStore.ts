import { create } from "zustand";

export interface KairosUser {
  uid: string;
  name: string | null;
  email: string | null;
  photoUrl: string | null;
}

interface AuthState {
  user: KairosUser | null;
  authReady: boolean;
  setUser: (u: KairosUser | null) => void;
  setAuthReady: (b: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  authReady: false,
  setUser: (user) => set({ user }),
  setAuthReady: (authReady) => set({ authReady }),
}));
