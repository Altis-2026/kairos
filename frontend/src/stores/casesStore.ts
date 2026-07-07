import { create } from "zustand";
import type { BBox } from "../types/map";

export interface SavedCase {
  id: string;
  userId: string;
  analysisType: string;
  displayName: string;
  bbox: BBox;
  startDate: string;
  endDate: string;
  dataDate: string;
  headlineLabel: string;
  headlineValue: number;
  headlineUnit: string;
  createdAt: number;
}

interface CasesState {
  cases: SavedCase[];
  loading: boolean;
  error: string | null;
  setCases: (cases: SavedCase[]) => void;
  addCase: (c: SavedCase) => void;
  removeCase: (id: string) => void;
  setLoading: (b: boolean) => void;
  setError: (e: string | null) => void;
}

export const useCasesStore = create<CasesState>((set) => ({
  cases: [],
  loading: false,
  error: null,
  setCases: (cases) => set({ cases }),
  addCase: (c) =>
    set((s) => ({ cases: [c, ...s.cases.filter((x) => x.id !== c.id)] })),
  removeCase: (id) => set((s) => ({ cases: s.cases.filter((c) => c.id !== id) })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
