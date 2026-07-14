/**
 * Janus mentor state. Lives in a store (not panel-local state) so an open
 * conversation survives closing and reopening the panel mid-analysis.
 */
import { create } from "zustand";
import {
  createProject,
  deleteProject,
  dismissInsight,
  fetchCurricula,
  fetchEntitlements,
  fetchJanusStatus,
  getProject,
  listProjects,
  sendChat,
  toggleWatch,
  type Curriculum,
  type Entitlements,
  type Insight,
  type JanusMessage,
  type JanusMode,
  type ProjectBundle,
  type JanusProject,
} from "../api/janus";

interface JanusState {
  available: boolean | null;
  entitlements: Entitlements | null;
  projects: JanusProject[];
  curricula: Curriculum[];
  bundle: ProjectBundle | null;
  loadingHome: boolean;
  openingId: number | null;
  sending: boolean;
  watchBusy: boolean;
  error: string | null;

  loadHome: () => Promise<void>;
  open: (id: number) => Promise<void>;
  startProject: (
    title: string,
    question: string,
    curriculumId: string | null
  ) => Promise<void>;
  send: (message: string, mode: JanusMode) => Promise<void>;
  setWatch: (watch: boolean) => Promise<void>;
  dismiss: (insightId: number) => Promise<void>;
  backToList: () => void;
  remove: (id: number) => Promise<void>;
  clearError: () => void;
}

export const useJanusStore = create<JanusState>((set, get) => ({
  available: null,
  entitlements: null,
  projects: [],
  curricula: [],
  bundle: null,
  loadingHome: false,
  openingId: null,
  sending: false,
  watchBusy: false,
  error: null,

  loadHome: async () => {
    set({ loadingHome: true, error: null });
    try {
      const [status, projects, curricula, entitlements] = await Promise.all([
        fetchJanusStatus(),
        listProjects(),
        fetchCurricula(),
        fetchEntitlements().catch(() => null),
      ]);
      set({
        available: status.available,
        projects: projects.projects,
        curricula: curricula.curricula,
        entitlements,
        loadingHome: false,
      });
    } catch (e) {
      set({
        loadingHome: false,
        available: false,
        error: e instanceof Error ? e.message : "Couldn't reach Janus.",
      });
    }
  },

  open: async (id) => {
    set({ openingId: id, error: null });
    try {
      const bundle = await getProject(id);
      set({ bundle, openingId: null });
    } catch (e) {
      set({
        openingId: null,
        error: e instanceof Error ? e.message : "Couldn't open the project.",
      });
    }
  },

  startProject: async (title, question, curriculumId) => {
    set({ openingId: -1, error: null });
    try {
      const bundle = await createProject(title, question, curriculumId);
      set((s) => ({
        bundle: {
          ...bundle,
          insights: bundle.insights ?? [],
          hypotheses: bundle.hypotheses ?? [],
        },
        projects: [bundle.project, ...s.projects],
        openingId: null,
      }));
    } catch (e) {
      set({
        openingId: null,
        error: e instanceof Error ? e.message : "Couldn't create the project.",
      });
    }
  },

  send: async (message, mode) => {
    const { bundle } = get();
    if (!bundle || get().sending) return;
    // Optimistic user bubble; the server persists the real one.
    const local: JanusMessage = {
      id: -Date.now(),
      project_id: bundle.project.id,
      role: "user",
      content: message,
      mode,
      tool_events: [],
      created_at: Date.now() / 1000,
    };
    set({
      sending: true,
      error: null,
      bundle: { ...bundle, messages: [...bundle.messages, local] },
    });
    try {
      const turn = await sendChat(bundle.project.id, message, mode);
      set((s) => ({
        sending: false,
        bundle: s.bundle
          ? {
              project: turn.project,
              messages: [...s.bundle.messages, turn.message],
              bibliography: turn.bibliography,
              insights: s.bundle.insights,
              hypotheses: turn.hypotheses ?? s.bundle.hypotheses,
            }
          : s.bundle,
        projects: s.projects.map((p) =>
          p.id === turn.project.id ? turn.project : p
        ),
      }));
    } catch (e) {
      set({
        sending: false,
        error:
          e instanceof Error ? e.message : "The mentor turn failed. Try again.",
      });
    }
  },

  setWatch: async (watch) => {
    const { bundle } = get();
    if (!bundle || get().watchBusy) return;
    set({ watchBusy: true, error: null });
    try {
      const res = await toggleWatch(bundle.project.id, watch);
      set((s) => ({
        watchBusy: false,
        bundle: s.bundle
          ? {
              ...s.bundle,
              project: res.project,
              insights: res.insights ?? s.bundle.insights,
            }
          : s.bundle,
        projects: s.projects.map((p) =>
          p.id === res.project.id ? res.project : p
        ),
      }));
    } catch (e) {
      set({
        watchBusy: false,
        error:
          e instanceof Error ? e.message : "Couldn't change monitoring.",
      });
    }
  },

  dismiss: async (insightId) => {
    // Optimistic removal; the row is only hidden, never deleted server-side.
    set((s) => ({
      bundle: s.bundle
        ? {
            ...s.bundle,
            insights: s.bundle.insights.filter((i: Insight) => i.id !== insightId),
          }
        : s.bundle,
    }));
    try {
      await dismissInsight(insightId);
    } catch {
      /* non-fatal: it reappears on next load if the call failed */
    }
  },

  backToList: () => {
    set({ bundle: null });
    void get().loadHome();
  },

  remove: async (id) => {
    try {
      await deleteProject(id);
      set((s) => ({
        projects: s.projects.filter((p) => p.id !== id),
        bundle: s.bundle?.project.id === id ? null : s.bundle,
      }));
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Couldn't delete the project.",
      });
    }
  },

  clearError: () => set({ error: null }),
}));
