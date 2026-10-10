import { apiFetch } from "./client";
import type { QueryResponse } from "../types/analysis";
import type { BBox } from "../types/map";

export interface ConversationTurn {
  role: "user" | "kairos";
  content: string;
}

export function runQuery(
  query: string,
  viewportBbox?: BBox,
  history?: ConversationTurn[],
  options: { signal?: AbortSignal; language?: string } = {}
): Promise<QueryResponse> {
  return apiFetch<QueryResponse>("/query", {
    method: "POST",
    signal: options.signal,
    body: JSON.stringify({
      query,
      viewport_bbox: viewportBbox ?? null,
      history: history && history.length ? history : null,
      language: options.language ?? navigator.language ?? null,
    }),
  });
}
