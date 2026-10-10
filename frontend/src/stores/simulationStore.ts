import { create } from "zustand";
import { suggestedDepthScaleM } from "../lib/simulation";
import type { DecodedFire, DecodedSimulation } from "../types/simulation";

export type SimStatus = "idle" | "running" | "ready" | "error";

export const SPEEDS = [0.5, 1, 2, 4] as const;

interface SimulationState {
  sim: DecodedSimulation | null;

  fire: DecodedFire | null;
  status: SimStatus;
  error: string | null;

  progressNote: string | null;

  frame: number;
  playing: boolean;
  speed: number;

  showFlood: boolean;
  showTerrain: boolean;

  frontMinutes: number;

  view3d: boolean;
  opacity: number;

  depthScaleM: number;

  setStatus: (status: SimStatus, error?: string | null) => void;
  setProgressNote: (note: string | null) => void;
  loadSimulation: (sim: DecodedSimulation) => void;
  loadFire: (fire: DecodedFire) => void;
  clearSimulation: () => void;

  setFrame: (frame: number) => void;
  stepFrame: (delta: number) => void;
  setPlaying: (playing: boolean) => void;
  togglePlaying: () => void;
  cycleSpeed: () => void;

  setView3d: (on: boolean) => void;
  setShowFlood: (on: boolean) => void;
  setShowTerrain: (on: boolean) => void;
  setOpacity: (opacity: number) => void;
  setDepthScaleM: (depth: number) => void;
  setFrontMinutes: (minutes: number) => void;
}

export const useSimulationStore = create<SimulationState>((set, get) => ({
  sim: null,
  fire: null,
  status: "idle",
  error: null,
  progressNote: null,

  frame: 0,
  playing: false,
  speed: 1,

  showFlood: true,
  showTerrain: true,
  view3d: false,
  opacity: 0.9,
  depthScaleM: 1,
  frontMinutes: 12,

  setStatus: (status, error = null) => set({ status, error }),
  setProgressNote: (progressNote) => set({ progressNote }),

  loadSimulation: (sim) =>
    set({
      sim,
      fire: null,
      status: "ready",
      error: null,
      progressNote: null,
      frame: 0,
      playing: true,

      depthScaleM: suggestedDepthScaleM(sim),
    }),

  loadFire: (fire) =>
    set({
      fire,
      sim: null,
      status: "ready",
      error: null,
      progressNote: null,
      frame: 0,
      playing: true,
    }),

  clearSimulation: () =>
    set({
      sim: null,
      fire: null,
      status: "idle",
      error: null,
      progressNote: null,
      frame: 0,
      playing: false,
      view3d: false,
    }),

  setFrame: (frame) => {
    const frames = get().sim?.frames ?? get().fire?.frames;
    if (!frames) return;
    set({ frame: Math.min(Math.max(frame, 0), frames - 1) });
  },

  stepFrame: (delta) => {
    const { sim, fire, frame } = get();
    const frames = sim?.frames ?? fire?.frames;
    if (!frames) return;
    set({ frame: Math.min(Math.max(frame + delta, 0), frames - 1) });
  },

  setPlaying: (playing) => set({ playing }),
  togglePlaying: () => set((s) => ({ playing: !s.playing })),
  cycleSpeed: () => set((s) => ({ speed: SPEEDS[(SPEEDS.indexOf(s.speed as 1) + 1) % SPEEDS.length] })),

  setView3d: (view3d) => set({ view3d }),
  setShowFlood: (showFlood) => set({ showFlood }),
  setShowTerrain: (showTerrain) => set({ showTerrain }),
  setOpacity: (opacity) => set({ opacity }),
  setDepthScaleM: (depthScaleM) => set({ depthScaleM }),
  setFrontMinutes: (frontMinutes) => set({ frontMinutes }),
}));
