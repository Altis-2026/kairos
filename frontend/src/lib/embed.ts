/**
 * Embeddable widgets + public-view routing.
 *
 * Kairos is a single-page app, so "routes" are encoded in the URL hash (the
 * same mechanism the share links already use):
 *   #watch                      -> the public Live Watch dashboard (no login)
 *   #embed&task=..&bbox=..&..   -> a minimal embeddable result widget
 *   #task=..&bbox=..&..         -> normal app + restore a shared analysis
 *
 * An embed renders one analysis on a bare map with a credit badge, so a news
 * site or NGO can <iframe> a live Kairos result into their own page.
 */
import type { BBox } from "../types/map";
import type { CaseRef } from "./share";

export type Route = "watch" | "embed" | "app";

export function getRoute(): Route {
  const hash = location.hash.replace(/^#/, "");
  if (hash === "watch") return "watch";
  if (hash.startsWith("embed")) return "embed";
  return "app";
}

/** Parse the embed hash (#embed&task=..&bbox=..&start=..&end=..). */
export function parseEmbedHash(): CaseRef | null {
  const hash = location.hash.replace(/^#/, "");
  if (!hash.startsWith("embed")) return null;
  // Drop the leading "embed&" (or "embed") marker before reading params.
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

/** A ready-to-paste responsive iframe snippet for the given result. */
export function buildEmbedSnippet(ref: CaseRef): string {
  const url = buildEmbedUrl(ref);
  return `<iframe src="${url}" width="640" height="420" style="border:0;border-radius:12px;max-width:100%" loading="lazy" title="Kairos SAR analysis" allowfullscreen></iframe>`;
}
