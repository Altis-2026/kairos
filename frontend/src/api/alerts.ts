import { apiFetch } from "./client";
import type { BBox } from "../types/map";
import type { AlertCheckResponse } from "../types/analysis";

export function checkAlert(p: {
  analysis_type: string;
  bbox: BBox;
  since_date?: string | null;
  lookback_days?: number;
}): Promise<AlertCheckResponse> {
  return apiFetch<AlertCheckResponse>("/alerts/check", {
    method: "POST",
    body: JSON.stringify(p),
  });
}
