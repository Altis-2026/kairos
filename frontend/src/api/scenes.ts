import { apiFetch } from "./client";
import type { ScenesResponse } from "../types/analysis";
import type { BBox } from "../types/map";

export function fetchScenes(
  bbox: BBox,
  startDate: string,
  endDate: string
): Promise<ScenesResponse> {
  const params = new URLSearchParams({
    min_lon: String(bbox[0]),
    min_lat: String(bbox[1]),
    max_lon: String(bbox[2]),
    max_lat: String(bbox[3]),
    start_date: startDate,
    end_date: endDate,
  });
  return apiFetch<ScenesResponse>(`/scenes?${params.toString()}`);
}
