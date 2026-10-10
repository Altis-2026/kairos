import { apiFetch } from "./client";
import type { AnalysisResult } from "../types/analysis";
import type { BBox } from "../types/map";

export interface AnalyzeParams {
  analysis_type: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
  polygon?: [number, number][] | null;
}

export function runAnalyze(params: AnalyzeParams): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>("/analyze", {
    method: "POST",
    body: JSON.stringify(params),
  });
}
