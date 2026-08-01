import { apiFetch, API_BASE } from "./client";
import type { BBox } from "../types/map";

export interface InsarSite {
  id: string;
  name: string;
  region: string;
  bbox: BBox;
  description: string;
  product: string;
  source: string;
  source_url: string;
  dates: [string, string] | null;
  frame: string | null;
  available: boolean;
  layers: { interferogram: string | null; coherence: string | null };
}

export function fetchInsarSites(): Promise<{ sites: InsarSite[] }> {
  return apiFetch<{ sites: InsarSite[] }>("/insar/sites");
}

export function insarLayerUrl(path: string): string {
  return `${API_BASE}${path}`;
}
