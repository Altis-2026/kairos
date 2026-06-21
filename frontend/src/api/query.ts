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
  history?: ConversationTurn[]
): Promise<QueryResponse> {
  return apiFetch<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify({
      query,
      viewport_bbox: viewportBbox ?? null,
      history: history && history.length ? history : null,
    }),
  });
}
