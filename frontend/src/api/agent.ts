import { apiFetch } from "./client";
import type { BBox } from "../types/map";
import type { ConversationTurn } from "./query";

export interface MissionStep {
  analysis_type: string;
  location_name: string | null;
  bbox: BBox;
  start_date: string;
  end_date: string;
  purpose: string | null;
}

export interface MissionPlanResponse {
  understood: boolean;
  plan_summary: string | null;
  steps: MissionStep[] | null;
  clarification: string | null;
}

export interface MissionOutcome {
  analysis_type: string;
  display_name?: string;
  location_name?: string | null;
  status: "ok" | "no_data" | "failed";
  headline_label?: string;
  headline_value?: number;
  headline_unit?: string;
  data_date?: string;
  detail?: string;
}

export function planMission(
  goal: string,
  viewportBbox?: BBox,
  history?: ConversationTurn[]
): Promise<MissionPlanResponse> {
  return apiFetch<MissionPlanResponse>("/agent/plan", {
    method: "POST",
    body: JSON.stringify({
      goal,
      viewport_bbox: viewportBbox ?? null,
      history: history && history.length ? history : null,
    }),
  });
}

export function missionReport(params: {
  goal: string;
  plan_summary: string | null;
  outcomes: MissionOutcome[];
}): Promise<{ report: string }> {
  return apiFetch<{ report: string }>("/agent/report", {
    method: "POST",
    body: JSON.stringify(params),
  });
}
