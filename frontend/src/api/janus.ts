/** Typed client for the Janus mentor API. */
import { apiFetch } from "./client";
import { useAuthStore } from "../stores/authStore";
import type { AnalysisResult } from "../types/analysis";

export interface JanusProject {
  id: number;
  owner: string;
  title: string;
  question: string;
  stage: "exploring" | "designing" | "analyzing" | "validating" | "writing";
  curriculum_id: string | null;
  curriculum_session: number;
  design: StudyDesign;
  created_at: number;
  updated_at: number;
}

export interface StudyDesign {
  hypothesis?: string;
  place?: string;
  bbox?: [number, number, number, number];
  start_date?: string;
  end_date?: string;
  analysis_types?: string[];
  confounders?: string[];
  validation_plan?: string;
}

export interface JanusPaper {
  title: string;
  authors: string;
  year: number | null;
  venue: string | null;
  doi: string | null;
  cited_by: number;
  abstract_snippet: string;
}

export interface ToolEvent {
  tool: string;
  label: string;
  status: "ok" | "empty" | "error";
  result?: AnalysisResult;
  papers?: JanusPaper[];
  datasets?: Record<string, string>[];
  design?: StudyDesign;
  validation?: Record<string, unknown>;
}

export interface JanusMessage {
  id: number;
  project_id: number;
  role: "user" | "assistant";
  content: string;
  mode: string | null;
  tool_events: ToolEvent[];
  created_at: number;
}

export interface Reference {
  id: number;
  title: string;
  authors: string | null;
  year: number | null;
  venue: string | null;
  url: string | null;
  note: string | null;
}

export interface Curriculum {
  id: string;
  title: string;
  audience: string;
  outcome: string;
  sessions: string[];
}

export type JanusMode = "mentor" | "design" | "review";

const OWNER_KEY = "kairos_janus_owner";

/** Stable owner id: the Firebase uid when signed in, else a per-browser id. */
export function janusOwner(): string {
  const user = useAuthStore.getState().user;
  if (user?.uid) return user.uid;
  try {
    let anon = localStorage.getItem(OWNER_KEY);
    if (!anon) {
      anon = `anon-${crypto.randomUUID()}`;
      localStorage.setItem(OWNER_KEY, anon);
    }
    return anon;
  } catch {
    return "anon-session";
  }
}

export function fetchJanusStatus(): Promise<{ available: boolean }> {
  return apiFetch("/janus/status");
}

export function fetchCurricula(): Promise<{ curricula: Curriculum[] }> {
  return apiFetch("/janus/curricula");
}

export function listProjects(): Promise<{ projects: JanusProject[] }> {
  return apiFetch(`/janus/projects?owner=${encodeURIComponent(janusOwner())}`);
}

export interface ProjectBundle {
  project: JanusProject;
  messages: JanusMessage[];
  bibliography: Reference[];
}

export function createProject(
  title: string,
  question = "",
  curriculumId: string | null = null
): Promise<ProjectBundle> {
  return apiFetch("/janus/projects", {
    method: "POST",
    body: JSON.stringify({
      owner: janusOwner(),
      title,
      question,
      curriculum_id: curriculumId,
    }),
  });
}

export function getProject(id: number): Promise<ProjectBundle> {
  return apiFetch(
    `/janus/projects/${id}?owner=${encodeURIComponent(janusOwner())}`
  );
}

export function deleteProject(id: number): Promise<{ deleted: boolean }> {
  return apiFetch(
    `/janus/projects/${id}?owner=${encodeURIComponent(janusOwner())}`,
    { method: "DELETE" }
  );
}

export interface ChatTurn {
  message: JanusMessage;
  project: JanusProject;
  bibliography: Reference[];
}

export function sendChat(
  projectId: number,
  message: string,
  mode: JanusMode
): Promise<ChatTurn> {
  return apiFetch(`/janus/projects/${projectId}/chat`, {
    method: "POST",
    body: JSON.stringify({ owner: janusOwner(), message, mode }),
  });
}
