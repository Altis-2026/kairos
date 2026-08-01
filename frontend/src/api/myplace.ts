import { apiFetch } from "./client";
import type { BBox } from "../types/map";

export interface PlaceHit {
  found: boolean;
  label?: string;
  lon?: number;
  lat?: number;
  bbox?: BBox;
  source?: string;
}

export function locatePlace(address: string): Promise<PlaceHit> {
  return apiFetch<PlaceHit>("/myplace/locate", {
    method: "POST",
    body: JSON.stringify({ address }),
  });
}
