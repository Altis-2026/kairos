import { apiFetch, ApiError } from "./client";
import type { FirePayload, SimulationPayload } from "../types/simulation";

export type SimulationKind = "flood" | "fire";

export interface SimulationScene {
  id: string;
  name: string;
  region: string;
  bbox: number[];
  summary: string;
  duration_hours: number;
  scale_m: number;
  disclosure: string;
  tags: string[];
  mode: string;
  kind: SimulationKind;

  peak_discharge_m3s?: number;
  rise_minutes?: number;
  peak_minutes?: number;
  recession_minutes?: number;
  n_manning?: number;

  fuel_model?: string;
  wind_ms?: number;
  wind_from_bearing?: number;
  ignition_point?: number[];
}

export interface SimulationResult {
  analysis_type: string;
  display_name: string;
  bbox: number[];
  start_date: string;
  mode: string;
  confidence: number;
  headline_stat: { label: string; value: number; unit: string };
  simulation: SimulationPayload | FirePayload;
  stats: Record<string, unknown>;
}

interface QueuedResponse {
  job_id: string;
  status: string;
  poll: string;
}

interface JobStatusResponse {
  job_id: string;
  status: string;
  result: SimulationResult | null;
  error?: string;
}

export async function fetchScenes(kind?: SimulationKind): Promise<{
  scenes: SimulationScene[];
  note: string;
}> {
  return apiFetch(`/simulate/scenes${kind ? `?kind=${kind}` : ""}`);
}

const POLL_TIMEOUT_MS = 10 * 60 * 1000;
const POLL_INTERVAL_MS = 2000;

export async function runSimulation(
  body: {
    kind?: SimulationKind;
    scene?: string;
    bbox?: number[];
    start_date?: string;
    params?: Record<string, unknown>;
  },
  onProgress?: (note: string) => void
): Promise<SimulationResult> {
  const response = await apiFetch<SimulationResult | QueuedResponse>("/simulate", {
    method: "POST",
    body: JSON.stringify({ run_async: true, ...body }),
  });

  if (!("job_id" in response)) return response as SimulationResult;

  const { job_id } = response as QueuedResponse;
  onProgress?.("Queued, solving on the worker…");

  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    const status = await apiFetch<JobStatusResponse>(`/status/${job_id}`);
    if (status.status === "complete" && status.result) return status.result;
    if (status.status === "failed") {
      throw new ApiError(500, status.error || "The simulation job failed.");
    }
    onProgress?.(status.status === "started" ? "Solving…" : `Job ${status.status}…`);
  }
  throw new ApiError(504, "The simulation is still running. Try a smaller area.");
}
