import { apiFetch } from "./client";
import type { AnalysisResult } from "../types/analysis";
import type { BBox } from "../types/map";

export interface FeaturedStory {
  id: string;
  title: string;
  place: string;
  when: string;
  summary: string;
  analysis_type: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
}

export function fetchFeatured(): Promise<{ stories: FeaturedStory[]; status: Record<string, string> }> {
  return apiFetch("/featured");
}

export function runFeaturedStory(id: string): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>(`/featured/${encodeURIComponent(id)}`, { method: "POST" });
}
