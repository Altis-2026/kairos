import { apiFetch } from "./client";
import type { BBox } from "../types/map";
import type { InterpretResponse } from "../types/analysis";

/** Everything the backend needs to ground an interpretation in real numbers. */
export interface InterpretInput {
  analysis_type: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
  display_name?: string;
  place_name?: string;
  data_date?: string;
  confidence?: number;
  headline_label?: string;
  headline_value?: number;
  headline_unit?: string;
  stats?: Record<string, unknown>;
}

/** Instant, grounded "what does this mean?" — works with or without an AI key. */
export function fetchInterpretation(p: InterpretInput): Promise<InterpretResponse> {
  return apiFetch<InterpretResponse>("/interpret", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

/** On-demand: recent regional news / trends / concerns via web search. */
export function fetchRegionalContext(p: InterpretInput): Promise<InterpretResponse> {
  return apiFetch<InterpretResponse>("/interpret/context", {
    method: "POST",
    body: JSON.stringify(p),
  });
}
