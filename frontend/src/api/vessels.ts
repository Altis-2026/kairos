import { apiFetch } from "./client";
import type { BBox } from "../types/map";

export interface VesselCase {
  id: string;
  name: string;
  region: string;
  bbox: BBox;
  target_date: string;
  why: string;
  ais_source: string;
  ais_url: string;
  available: boolean;
}

export interface ScreenResult {
  case: VesselCase;
  radar_time_utc: string;
  data_date: string;
  tile_url: string;
  detections_total: number;
  matched_count: number;
  unmatched_count: number;
  ais_vessels_in_window: number;
  match_radius_m: { base: number; typical: number; max: number };
  matched: GeoJSON.FeatureCollection;
  unmatched: GeoJSON.FeatureCollection;
  ais_window: { from: string; to: string } | null;
  headline_stat: { label: string; value: number; unit: string };
  caveats: string[];
}

export function listVesselCases(): Promise<{ cases: VesselCase[] }> {
  return apiFetch<{ cases: VesselCase[] }>("/vessels/cases");
}

export function screenCase(caseId: string): Promise<ScreenResult> {
  return apiFetch<ScreenResult>("/vessels/screen", {
    method: "POST",
    body: JSON.stringify({ case_id: caseId }),
  });
}
