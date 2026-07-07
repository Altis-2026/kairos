import type { BBox } from "../types/map";
import type { CaseRef } from "./share";

export type Route = "watch" | "guardian" | "embed" | "app" | "landing";

export function goToApp(e?: { preventDefault: () => void }) {
  e?.preventDefault();
  location.hash = "app";
  location.reload();
}

export function getRoute(): Route {
  const hash = location.hash.replace(/^#/, "");
  if (hash === "watch") return "watch";
  if (hash === "guardian") return "guardian";
  if (hash.startsWith("embed")) return "embed";
  if (!hash) return "landing";
  return "app";
}

export function parseEmbedHash(): CaseRef | null {
  const hash = location.hash.replace(/^#/, "");
  if (!hash.startsWith("embed")) return null;

  const qs = hash.replace(/^embed&?/, "");
  const p = new URLSearchParams(qs);
  const task = p.get("task");
  const bboxStr = p.get("bbox");
  const start = p.get("start");
  const end = p.get("end");
  if (!task || !bboxStr || !start || !end) return null;
  const parts = bboxStr.split(",").map(Number);
  if (parts.length !== 4 || parts.some((n) => Number.isNaN(n))) return null;
  return {
    analysis_type: task,
    bbox: [parts[0], parts[1], parts[2], parts[3]] as BBox,
    start_date: start,
    end_date: end,
  };
}

export function buildEmbedUrl(ref: CaseRef): string {
  const params = new URLSearchParams({
    task: ref.analysis_type,
    bbox: ref.bbox.join(","),
    start: ref.start_date,
    end: ref.end_date,
  });
  return `${location.origin}${location.pathname}#embed&${params.toString()}`;
}

export function buildEmbedSnippet(ref: CaseRef): string {
  const url = buildEmbedUrl(ref);
  return `<iframe src="${url}" width="640" height="420" style="border:0;border-radius:12px;max-width:100%" loading="lazy" title="Kairos SAR analysis" allowfullscreen></iframe>`;
}
