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
