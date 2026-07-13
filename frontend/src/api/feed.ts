import { apiFetch } from "./client";
import type { BBox } from "../types/map";

export interface Finding {
  id: number;
  source: "eonet" | "watchlist";
  source_title: string | null;
  source_link: string | null;
  region: string;
  analysis_type: string;
  display_name: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
  data_date: string | null;
  headline_label: string | null;
  headline_value: number | null;
  headline_unit: string | null;
  confidence: number | null;
  summary: string | null;
  created_at: number;
}

export interface SweepInfo {
  started_at: number;
  finished_at: number | null;
  targets: number;
  findings: number;
  errors: number;
}

export interface FeedResponse {
  available: boolean;
  findings: Finding[];
  count: number;
  sweeping: boolean;
  last_sweep: SweepInfo | null;
  next_sweep_at: number | null;
  interval_hours: number;
}

export function fetchFeed(limit = 40): Promise<FeedResponse> {
  return apiFetch<FeedResponse>(`/feed?limit=${limit}`);
}

export function triggerSweep(): Promise<{ started: boolean; reason?: string }> {
  return apiFetch("/feed/sweep", { method: "POST" });
}

export const ANALYSIS_COLORS: Record<string, string> = {
  flood_extent: "#00BFA8",
  flood_depth: "#1E6FE8",
  ship_detection: "#E8A318",
  wildfire_burn_scar: "#E8541E",
  oil_spill: "#7B61FF",
  deforestation: "#E84855",
  sea_ice: "#BFEFFF",
  surface_deformation: "#C77DFF",
  building_damage: "#FF3B5C",
  land_subsidence: "#1E6FE8",
  urban_growth: "#E8A318",
  crop_monitoring: "#7BC043",
  land_disturbance: "#FF6B2C",
};

export function timeAgo(epochSeconds: number): string {
  const diff = Date.now() / 1000 - epochSeconds;
  if (diff < 90) return "just now";
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}
