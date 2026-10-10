import { apiFetch } from "./client";
import type { BBox } from "../types/map";

export interface District {
  found: boolean;
  note?: string;
  name?: string;
  label?: string;
  state_abbr?: string;
  state_name?: string;
  district_number?: string;
  ring?: [number, number][];
  bbox?: BBox;
  vertex_count?: number;
}

export function locateDistrict(lon: number, lat: number): Promise<District> {
  return apiFetch<District>(`/districts/locate?lon=${lon}&lat=${lat}`);
}

export function lookupDistrict(state: string, number: string): Promise<District> {
  const params = new URLSearchParams({ state, number });
  return apiFetch<District>(`/districts/lookup?${params.toString()}`);
}
