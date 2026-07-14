/** Typed client for the Janus mentor API. */
import { apiFetch, API_BASE } from "./client";
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
  watched: number;
  created_at: number;
  updated_at: number;
}

export interface InsightAction {
  type: string;
  analysis_type?: string;
  bbox?: [number, number, number, number];
  start_date?: string;
  end_date?: string;
  label?: string;
}

export interface Insight {
  id: number;
  project_id: number;
  kind: string;
  content: string;
  action: InsightAction | null;
  dismissed: number;
  created_at: number;
}

export interface Entitlements {
  tier: string;
  tier_name: string;
  blurb: string;
  features: string[];
  project_cap: number | null;
  catalog: { id: string; name: string; price_usd_month: number; blurb: string }[];
  unread_insights: number;
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

export interface ConceptResource {
  name: string;
  url: string;
}

export interface ConceptPrimer {
  id?: string;
  title: string;
  explanation: string;
  resources: ConceptResource[];
}

export interface ToolEvent {
  tool: string;
  label: string;
  status: "ok" | "empty" | "error";
  result?: AnalysisResult;
  concept?: ConceptPrimer;
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

export function fetchEntitlements(): Promise<Entitlements> {
  return apiFetch(`/janus/entitlements?owner=${encodeURIComponent(janusOwner())}`);
}

export function listProjects(): Promise<{ projects: JanusProject[] }> {
  return apiFetch(`/janus/projects?owner=${encodeURIComponent(janusOwner())}`);
}

export interface ProjectBundle {
  project: JanusProject;
  messages: JanusMessage[];
  bibliography: Reference[];
  insights: Insight[];
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

export interface WatchResult {
  project: JanusProject;
  new_insight: boolean;
  insights?: Insight[];
  check_error?: string;
}

export function toggleWatch(
  projectId: number,
  watch: boolean
): Promise<WatchResult> {
  return apiFetch(`/janus/projects/${projectId}/watch`, {
    method: "POST",
    body: JSON.stringify({ owner: janusOwner(), watch }),
  });
}

export function dismissInsight(insightId: number): Promise<{ dismissed: boolean }> {
  return apiFetch(`/janus/insights/${insightId}/dismiss`, { method: "POST" });
}

/** Build the reproducibility-pack download URL (auth via owner query param). */
export function packUrl(projectId: number): string {
  return `${API_BASE}/janus/projects/${projectId}/pack?owner=${encodeURIComponent(
    janusOwner()
  )}`;
}

/** Fetch the pack and trigger a browser download, keeping the owner param. */
export async function downloadPack(projectId: number, title: string) {
  const res = await fetch(packUrl(projectId));
  if (!res.ok) {
    let detail = `Export failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON */
    }
    throw new Error(detail);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const slug =
    title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 50) || "project";
  a.download = `kairos-research-pack-${slug}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
