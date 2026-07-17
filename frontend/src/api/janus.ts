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

export interface Skill {
  skill: string;
  level: "learning" | "practiced" | "confident";
  note: string | null;
  updated_at: number;
}

export interface Entitlements {
  tier: string;
  tier_name: string;
  blurb: string;
  features: string[];
  project_cap: number | null;
  catalog: { id: string; name: string; price_usd_month: number; blurb: string }[];
  unread_insights: number;
  skills: Skill[];
}

export interface Hypothesis {
  id: number;
  project_id: number;
  statement: string;
  status: "open" | "supported" | "refuted" | "inconclusive";
  evidence: string | null;
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
  /** True on the per-user always-on companion chat (hidden from lists). */
  companion?: boolean;
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

export interface ConfounderFinding {
  variable: string;
  finding: string;
  concern: "high" | "some" | "low";
}

export interface ConfounderReport {
  analysis_type: string;
  measurements: Record<string, unknown>;
  findings: ConfounderFinding[];
  overall_concern: "high" | "some" | "low";
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
  confounders?: ConfounderReport;
  hypothesis?: Hypothesis;
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

export type JanusMode = "mentor" | "design" | "review" | "autopilot";

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
  hypotheses: Hypothesis[];
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
  hypotheses: Hypothesis[];
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

function slugify(title: string): string {
  return (
    title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 50) || "project"
  );
}

/** Fetch a document endpoint and trigger a browser download. */
async function downloadDoc(path: string, filename: string) {
  const sep = path.includes("?") ? "&" : "?";
  const res = await fetch(
    `${API_BASE}${path}${sep}owner=${encodeURIComponent(janusOwner())}`
  );
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
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Download the Markdown reproducibility pack. */
export function downloadPack(projectId: number, title: string) {
  return downloadDoc(
    `/janus/projects/${projectId}/pack`,
    `kairos-research-pack-${slugify(title)}.md`
  );
}

/** Download the runnable Python Earth Engine script. */
export function downloadNotebook(projectId: number, title: string) {
  return downloadDoc(
    `/janus/projects/${projectId}/notebook`,
    `kairos_reproduce_${slugify(title).replace(/-/g, "_")}.py`
  );
}

/** Generate a peer-review report (Markdown string) for the project. */
export function fetchPeerReview(projectId: number): Promise<{ markdown: string }> {
  return apiFetch(
    `/janus/projects/${projectId}/review?owner=${encodeURIComponent(janusOwner())}`
  );
}

/** Download the Overleaf-ready LaTeX manuscript. */
export function downloadLatex(projectId: number, title: string) {
  return downloadDoc(
    `/janus/projects/${projectId}/latex`,
    `kairos-manuscript-${slugify(title)}.tex`
  );
}

/** Download the bibliography as BibTeX (Zotero / Mendeley / LaTeX). */
export function downloadBibtex(projectId: number, title: string) {
  return downloadDoc(
    `/janus/projects/${projectId}/bibtex`,
    `kairos-references-${slugify(title)}.bib`
  );
}

/** Download the bibliography as RIS (Zotero / Mendeley / EndNote). */
export function downloadRis(projectId: number, title: string) {
  return downloadDoc(
    `/janus/projects/${projectId}/ris`,
    `kairos-references-${slugify(title)}.ris`
  );
}

/** Download a Google Docs-importable HTML document. */
export function downloadGoogleDoc(projectId: number, title: string) {
  return downloadDoc(
    `/janus/projects/${projectId}/gdoc`,
    `kairos-doc-${slugify(title)}.html`
  );
}

/** Which publication figures have data for this project. */
export function fetchFigures(projectId: number): Promise<{ figures: string[] }> {
  return apiFetch(
    `/janus/projects/${projectId}/figures?owner=${encodeURIComponent(janusOwner())}`
  );
}

/** The URL of a figure SVG (for inline <img> preview). */
export function figureUrl(projectId: number, kind: string): string {
  return `${API_BASE}/janus/projects/${projectId}/figure/${kind}?owner=${encodeURIComponent(
    janusOwner()
  )}`;
}

/** Download a publication figure as SVG. */
export function downloadFigure(
  projectId: number,
  kind: string,
  title: string
) {
  return downloadDoc(
    `/janus/projects/${projectId}/figure/${kind}?download=true`,
    `kairos-${kind.replace(/_/g, "-")}-${slugify(title)}.svg`
  );
}

/** Download the one-page plain-language policy/decision brief. */
export function downloadPolicyBrief(projectId: number, title: string) {
  return downloadDoc(
    `/janus/projects/${projectId}/brief`,
    `kairos-brief-${slugify(title)}.html`
  );
}

export interface ProjectDataset {
  id: number;
  name: string;
  feature_count: number;
  bbox: [number, number, number, number] | null;
  created_at: number;
}

/** List the user's uploaded datasets on a project. */
export function listDatasets(
  projectId: number
): Promise<{ datasets: ProjectDataset[] }> {
  return apiFetch(
    `/janus/projects/${projectId}/datasets?owner=${encodeURIComponent(janusOwner())}`
  );
}

/** Upload field data (GeoJSON object or CSV text) to a project. */
export function uploadDataset(
  projectId: number,
  name: string,
  payload: { geojson?: unknown; csv?: string }
): Promise<{ dataset: ProjectDataset }> {
  return apiFetch(`/janus/projects/${projectId}/datasets`, {
    method: "POST",
    body: JSON.stringify({ owner: janusOwner(), name, ...payload }),
  });
}

/** Remove an uploaded dataset. */
export function deleteDataset(
  projectId: number,
  datasetId: number
): Promise<{ deleted: boolean }> {
  return apiFetch(
    `/janus/projects/${projectId}/datasets/${datasetId}?owner=${encodeURIComponent(
      janusOwner()
    )}`,
    { method: "DELETE" }
  );
}

/** Open (or create) the always-on companion chat — no project setup needed. */
export function fetchCompanion(): Promise<ProjectBundle> {
  return apiFetch("/janus/companion", {
    method: "POST",
    body: JSON.stringify({ owner: janusOwner() }),
  });
}
