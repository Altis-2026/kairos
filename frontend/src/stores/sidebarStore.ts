import { create } from "zustand";
import type { AnalysisResult, AnalysisType } from "../types/analysis";

export type SidebarStep =
  | "SELECT_TASK"
  | "DEFINE_AOI"
  | "CONFIGURE"
  | "PREVIEW_SCENES"
  | "RUNNING"
  | "RESULT";

export const STEP_ORDER: SidebarStep[] = [
  "SELECT_TASK",
  "DEFINE_AOI",
  "CONFIGURE",
  "PREVIEW_SCENES",
  "RUNNING",
  "RESULT",
];

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

interface SidebarState {
  open: boolean;
  step: SidebarStep;
  selectedTask: AnalysisType | null;
  startDate: string;
  endDate: string;
  baseline: "recent_12m" | "5y_average" | "custom";
  dataSource: "sentinel1" | "alos2" | "auto";
  result: AnalysisResult | null;
  error: string | null;

  openSidebar: () => void;
  closeSidebar: () => void;
  toggleSidebar: () => void;
  selectTask: (task: AnalysisType) => void;
  confirmAoi: () => void;
  confirmConfig: () => void;
  startRun: () => void;
  finishRun: (result: AnalysisResult) => void;
  failRun: (error: string) => void;
  goToStep: (step: SidebarStep) => void;
  setDates: (start: string, end: string) => void;
  setBaseline: (b: SidebarState["baseline"]) => void;
  setDataSource: (d: SidebarState["dataSource"]) => void;
  reset: () => void;
  compareNewDates: () => void;
}

export const useSidebarStore = create<SidebarState>((set) => ({
  open: false,
  step: "SELECT_TASK",
  selectedTask: null,
  startDate: isoDaysAgo(30),
  endDate: isoDaysAgo(0),
  baseline: "recent_12m",
  dataSource: "sentinel1",
  result: null,
  error: null,

  openSidebar: () => set({ open: true }),
  closeSidebar: () => set({ open: false }),
  toggleSidebar: () => set((s) => ({ open: !s.open })),
  selectTask: (task) =>
    set({ selectedTask: task, step: "DEFINE_AOI", error: null }),
  confirmAoi: () => set({ step: "CONFIGURE" }),
  confirmConfig: () => set({ step: "PREVIEW_SCENES" }),
  startRun: () => set({ step: "RUNNING", error: null, result: null }),
  finishRun: (result) => set({ step: "RESULT", result }),
  failRun: (error) => set({ step: "PREVIEW_SCENES", error }),
  goToStep: (step) => set({ step }),
  setDates: (startDate, endDate) => set({ startDate, endDate }),
  setBaseline: (baseline) => set({ baseline }),
  setDataSource: (dataSource) => set({ dataSource }),
  reset: () =>
    set({
      step: "SELECT_TASK",
      selectedTask: null,
      result: null,
      error: null,
    }),
  compareNewDates: () => set({ step: "CONFIGURE", result: null }),
}));
