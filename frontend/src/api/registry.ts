import { apiFetch } from "./client";
import type { AnalysisType } from "../types/analysis";

export function fetchRegistry(): Promise<AnalysisType[]> {
  return apiFetch<AnalysisType[]>("/registry");
}
