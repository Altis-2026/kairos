import { apiFetch } from "./client";
import type { BBox } from "../types/map";
import type { ImpactResponse } from "../types/analysis";

export function fetchImpact(p: {
  analysis_type: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
}): Promise<ImpactResponse> {
  return apiFetch<ImpactResponse>("/impact/population", {
    method: "POST",
    body: JSON.stringify(p),
  });
}
