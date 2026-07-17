import { apiFetch } from "./client";
import type { BBox } from "../types/map";
import type {
  CompareResponse,
  ResearchLayerResponse,
  TimeSeriesResponse,
} from "../types/analysis";

export interface AnalysisRef {
  analysis_type: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
}

export function fetchBackscatter(p: AnalysisRef): Promise<ResearchLayerResponse> {
  return apiFetch<ResearchLayerResponse>("/research/backscatter", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

export function fetchOptical(p: {
  bbox: BBox;
  start_date: string;
  end_date: string;
}): Promise<ResearchLayerResponse> {
  return apiFetch<ResearchLayerResponse>("/research/optical", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

export function fetchPopulationDensity(p: {
  bbox: BBox;
}): Promise<ResearchLayerResponse> {
  return apiFetch<ResearchLayerResponse>("/research/population", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

export function fetchCompare(p: AnalysisRef): Promise<CompareResponse> {
  return apiFetch<CompareResponse>("/research/compare", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

export function fetchTimeSeries(p: {
  analysis_type: string;
  bbox: BBox;
  end_date: string;
  steps?: number;
  interval_days?: number;
}): Promise<TimeSeriesResponse> {
  return apiFetch<TimeSeriesResponse>("/research/timeseries", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

export interface SignalPoint {
  date: string;
  value: number;
}

export interface TrendReport {
  ols: {
    slope_per_year: number;
    intercept: number;
    r_squared: number;
    p_value: number;
    n: number;
  };
  mann_kendall: {
    s: number;
    z: number;
    p_value: number;
    trend: string;
    sen_slope_per_year: number;
    n: number;
  };
  summary: string;
}

export interface SignalResponse {
  points: SignalPoint[];
  variable: string;
  unit: string;
  source: string;
  count: number;
  trend: TrendReport | null;
  csv: string;
  chart_svg: string;
}

/** Per-scene signal time series + trend statistics over an AOI. */
export function fetchSignal(p: {
  bbox: BBox;
  start_date: string;
  end_date: string;
  variable: string;
  source?: string;
}): Promise<SignalResponse> {
  return apiFetch<SignalResponse>("/research/signal", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

export interface ScoreboardEntry {
  benchmark_id: string;
  region: string;
  analysis_type: string;
  runs: number;
  mean_iou: number | null;
  mean_precision: number | null;
  mean_recall: number | null;
  mean_f1: number | null;
  latest_f1: number | null;
  last_run_at: number;
}

/** The public accuracy scoreboard (aggregated real validation runs). */
export function fetchScoreboard(): Promise<{
  entries: ScoreboardEntry[];
  total_runs: number;
  note: string;
}> {
  return apiFetch("/scoreboard");
}

/** Outbound webhook management (Slack-compatible alerts). */
export function saveWebhook(owner: string, url: string): Promise<{ saved: boolean }> {
  return apiFetch("/alerts/webhook", {
    method: "POST",
    body: JSON.stringify({ owner, url }),
  });
}

export function getWebhook(owner: string): Promise<{ url: string | null }> {
  return apiFetch(`/alerts/webhook?owner=${encodeURIComponent(owner)}`);
}

export function deleteWebhook(owner: string): Promise<{ deleted: boolean }> {
  return apiFetch(`/alerts/webhook?owner=${encodeURIComponent(owner)}`, {
    method: "DELETE",
  });
}

export function testWebhook(owner: string): Promise<{ delivered: boolean }> {
  return apiFetch("/alerts/webhook/test", {
    method: "POST",
    body: JSON.stringify({ owner }),
  });
}
