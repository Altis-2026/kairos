/**
 * Flood-simulation API client.
 *
 * POST /simulate either returns a finished result or, when a Redis worker is
 * available, a job id to poll — the backend picks based on what is running.
 * `runSimulation` handles both so callers do not have to care which
 * deployment they are talking to.
 */
import { apiFetch, ApiError } from "./client";
import type { SimulationPayload } from "../types/simulation";

export interface SimulationScene {
  id: string;
  name: string;
  region: string;
  bbox: number[];
  summary: string;
  peak_discharge_m3s: number;
  rise_minutes: number;
  peak_minutes: number;
  recession_minutes: number;
  duration_hours: number;
  n_manning: number;
  scale_m: number;
  disclosure: string;
  tags: string[];
  mode: string;
}

export interface SimulationResult {
  analysis_type: string;
  display_name: string;
  bbox: number[];
  start_date: string;
  mode: string;
  confidence: number;
  headline_stat: { label: string; value: number; unit: string };
  simulation: SimulationPayload;
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

export async function fetchScenes(): Promise<{
  scenes: SimulationScene[];
  note: string;
}> {
  return apiFetch("/simulate/scenes");
}

/** How long to keep polling a queued job before giving up. */
const POLL_TIMEOUT_MS = 10 * 60 * 1000;
const POLL_INTERVAL_MS = 2000;

export async function runSimulation(
  body: { scene?: string; bbox?: number[]; start_date?: string; params?: Record<string, unknown> },
  onProgress?: (note: string) => void
): Promise<SimulationResult> {
  const response = await apiFetch<SimulationResult | QueuedResponse>("/simulate", {
    method: "POST",
    body: JSON.stringify({ run_async: true, ...body }),
  });

  // Ran inline (no Redis worker) — the result is already here.
  if (!("job_id" in response)) return response as SimulationResult;

  const { job_id } = response as QueuedResponse;
  onProgress?.("Queued — solving on the worker…");

  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    const status = await apiFetch<JobStatusResponse>(`/status/${job_id}`);
    if (status.status === "complete" && status.result) return status.result;
    if (status.status === "failed") {
      throw new ApiError(500, status.error || "The simulation job failed.");
    }
    onProgress?.(
      status.status === "started" ? "Solving…" : `Job ${status.status}…`
    );
  }
  throw new ApiError(504, "The simulation is still running — try a smaller area.");
}
