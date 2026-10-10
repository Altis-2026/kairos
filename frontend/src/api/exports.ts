import { apiFetch } from "./client";
import type { BBox } from "../types/map";

export interface GeoTIFFResponse {
  download_url: string;
  filename: string;
  scale_m: number;
  data_date: string;
}

export interface ReportResponse {
  filename: string;
  markdown: string;
}

export interface GeoTIFFParams {
  analysis_type: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
}

export interface ReportParams {
  analysis_type: string;
  display_name: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
  data_date: string;
  confidence: number;
  headline_label: string;
  headline_value: number;
  headline_unit: string;
  stats?: Record<string, unknown>;
}

export function fetchGeoTIFF(p: GeoTIFFParams): Promise<GeoTIFFResponse> {
  return apiFetch<GeoTIFFResponse>("/export/geotiff", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

export function fetchReport(p: ReportParams): Promise<ReportResponse> {
  return apiFetch<ReportResponse>("/export/report", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

export interface BriefingFinding {
  analysis_type: string;
  display_name: string;
  headline_label: string;
  headline_value: number;
  headline_unit: string;
  data_date: string;
  start_date: string;
  end_date: string;
  confidence: number;
  summary?: string | null;
}

export interface BriefingParams {
  area_name: string;
  area_label?: string;
  area_km2?: number;
  prepared_for?: string;
  findings: BriefingFinding[];
}

export interface BriefingResponse {
  filename: string;
  html: string;
}

export function fetchBriefing(p: BriefingParams): Promise<BriefingResponse> {
  return apiFetch<BriefingResponse>("/export/briefing", {
    method: "POST",
    body: JSON.stringify(p),
  });
}
