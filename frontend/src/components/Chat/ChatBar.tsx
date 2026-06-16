/**
 * "Ask about this area…" — the natural language entry point.
 * Sends the query plus the current viewport bbox so "this area" resolves.
 */
import { useState } from "react";
import { ArrowUp } from "lucide-react";
import { runQuery } from "../../api/query";
import { useChatStore } from "../../stores/chatStore";
import { bboxCenterZoom, useMapStore } from "../../stores/mapStore";
import SuggestionChips from "./SuggestionChips";
import ChatMessages from "./ChatMessage";
import type { AnalysisResult } from "../../types/analysis";

let msgId = 0;
const nextId = () => `m${++msgId}-${Date.now()}`;

export function applyResultToGlobe(result: AnalysisResult) {
  const map = useMapStore.getState();
  const layerId = `${result.analysis_type}-${Date.now()}`;
  map.addRasterLayer({
    id: layerId,
    name: `${result.display_name} · ${result.data_date}`,
    tileUrl: result.tile_url,
    opacity: 0.85,
    visible: true,
    color: "#00BFA8",
  });
  const points = result.stats?.vessel_points as
    | GeoJSON.FeatureCollection
    | undefined;
  if (points?.features?.length) {
    map.addPointLayer({
      id: `${layerId}-pts`,
      name: `${result.display_name} points`,
      data: points,
      color: "#E8A318",
      visible: true,
    });
  }
  const { center, zoom } = bboxCenterZoom(result.bbox);
  map.requestFlyTo(center, zoom);
}

export default function ChatBar() {
  const [input, setInput] = useState("");
  const { addMessage, updateMessage, loading, setLoading } = useChatStore();

  async function send(text: string) {
    const query = text.trim();
    if (!query || loading) return;
    setInput("");
    addMessage({ id: nextId(), role: "user", text: query });
    const pendingId = nextId();
    addMessage({
      id: pendingId,
      role: "kairos",
      text: "Querying Sentinel-1 archive…",
      pending: true,
    });
    setLoading(true);

    try {
      const viewport = useMapStore.getState().viewportBbox ?? undefined;
      const res = await runQuery(query, viewport);

      if (!res.understood) {
        updateMessage(pendingId, {
          text: res.clarification ?? "Could you tell me more?",
          pending: false,
        });
        return;
      }
      if (res.result) {
        applyResultToGlobe(res.result);
      }
      updateMessage(pendingId, {
        text:
          res.explanation ??
          "Analysis complete — the result layer has been added to the globe.",
        pending: false,
      });
    } catch (e) {
      updateMessage(pendingId, {
        text:
          e instanceof Error
            ? e.message
            : "Something went wrong running that analysis.",
        pending: false,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="absolute bottom-5 inset-x-0 z-30 flex flex-col items-center gap-3 px-4 pointer-events-none">
      <ChatMessages />
      <SuggestionChips onPick={send} />
      <div className="w-full max-w-2xl pointer-events-auto">
        <div className="relative">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            placeholder="Ask about this area…"
            disabled={loading}
            className="w-full h-14 pl-6 pr-16 rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line text-[15px] text-ink placeholder-dim outline-none focus:ring-amber/60 shadow-panel transition-shadow disabled:opacity-70"
          />
          <button
            onClick={() => send(input)}
            disabled={loading || !input.trim()}
            title="Run query"
            className="absolute right-3 top-1/2 -translate-y-1/2 h-9 w-9 grid place-items-center rounded-xl bg-amber text-bg hover:brightness-110 transition disabled:opacity-40"
          >
            <ArrowUp size={17} />
          </button>
        </div>
      </div>
    </div>
  );
}
