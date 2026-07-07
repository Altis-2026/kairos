import { create } from "zustand";
import type { BBox } from "../types/map";

export interface SavedAlert {
  id: string;
  userId: string;
  label: string;
  analysisType: string;
  displayName: string;
  bbox: BBox;

  lastDataDate: string | null;
  lastHeadlineValue: number | null;
  lastHeadlineUnit: string | null;
  lastCheckedAt: number | null;
  createdAt: number;
}

interface AlertsState {
  alerts: SavedAlert[];
  loading: boolean;
  error: string | null;
  setAlerts: (alerts: SavedAlert[]) => void;
  addAlert: (a: SavedAlert) => void;
  updateAlert: (id: string, patch: Partial<SavedAlert>) => void;
  removeAlert: (id: string) => void;
  setLoading: (b: boolean) => void;
  setError: (e: string | null) => void;
}

export const useAlertsStore = create<AlertsState>((set) => ({
  alerts: [],
  loading: false,
  error: null,
  setAlerts: (alerts) => set({ alerts }),
  addAlert: (a) =>
    set((s) => ({ alerts: [a, ...s.alerts.filter((x) => x.id !== a.id)] })),
  updateAlert: (id, patch) =>
    set((s) => ({
      alerts: s.alerts.map((a) => (a.id === id ? { ...a, ...patch } : a)),
    })),
  removeAlert: (id) =>
    set((s) => ({ alerts: s.alerts.filter((a) => a.id !== id) })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
