/**
 * Shareable, reproducible case links.
 *
 * A link encodes the exact analysis type, bounding box and date window in the
 * URL hash — no database needed. Opening the link re-runs the same analysis, so
 * a colleague sees the identical result. This is intentionally stateless so
 * shares work for anyone, signed in or not.
 */
import type { BBox } from "../types/map";
import { runAnalyze } from "../api/analyze";
import { applyResultToGlobe } from "./applyResult";
import { useChatStore } from "../stores/chatStore";

export interface CaseRef {
  analysis_type: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
}

export function buildShareUrl(ref: CaseRef): string {
  const params = new URLSearchParams({
    task: ref.analysis_type,
    bbox: ref.bbox.join(","),
    start: ref.start_date,
    end: ref.end_date,
  });
  return `${location.origin}${location.pathname}#${params.toString()}`;
}

export function parseShareHash(): CaseRef | null {
  const hash = location.hash.replace(/^#/, "");
  if (!hash) return null;
  const p = new URLSearchParams(hash);
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

let restored = false;

/** On load, if the URL carries a shared case, re-run it onto the globe. */
export async function restoreFromHash(): Promise<void> {
  if (restored) return;
  const ref = parseShareHash();
  if (!ref) return;
  restored = true;
  // Swap the hash for the plain app route so a refresh doesn't re-trigger
  // the run (and doesn't bounce back out to the landing page).
  history.replaceState(null, "", location.pathname + location.search + "#app");

  const chat = useChatStore.getState();
  const id = `restore-${Date.now()}`;
  chat.addMessage({
    id,
    role: "kairos",
    text: "Restoring shared analysis…",
    pending: true,
  });
  try {
    const result = await runAnalyze(ref);
    applyResultToGlobe(result);
    chat.updateMessage(id, {
      text: `Restored: ${result.display_name} · ${result.data_date}.`,
      pending: false,
    });
  } catch (e) {
    chat.updateMessage(id, {
      text:
        e instanceof Error
          ? e.message
          : "Couldn't restore that shared link.",
      pending: false,
    });
  }
}
