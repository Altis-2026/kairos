import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, Flame, RotateCcw, Waves, X } from "lucide-react";
import { useChatStore, type ChatMessage } from "../../stores/chatStore";
import { useSimulationStore } from "../../stores/simulationStore";
import { simulateHere } from "../../lib/loadSimulation";
import { useT } from "../../lib/i18n";
import Markdown from "../Markdown";
import type { AnalysisResult } from "../../types/analysis";
import type { BBox } from "../../types/map";

const FLOOD_TYPES = new Set([
  "flood_extent",
  "flood_depth",
  "flood_consensus",
  "flooded_forest",
  "soil_moisture",
]);
const FIRE_TYPES = new Set(["wildfire_burn_scar", "fire_fusion"]);

function smallBox(bbox: BBox): BBox {
  const cx = (bbox[0] + bbox[2]) / 2;
  const cy = (bbox[1] + bbox[3]) / 2;
  const half = Math.min(0.08, (bbox[2] - bbox[0]) / 2, (bbox[3] - bbox[1]) / 2);
  return [cx - half, cy - half, cx + half, cy + half];
}

function ResultCard({ result }: { result: AnalysisResult }) {
  const t = useT();
  const simStatus = useSimulationStore((s) => s.status);
  const [busy, setBusy] = useState(false);
  const kind = FLOOD_TYPES.has(result.analysis_type)
    ? "flood"
    : FIRE_TYPES.has(result.analysis_type)
      ? "fire"
      : null;
  const hs = result.headline_stat;

  async function simulate() {
    if (!kind) return;
    setBusy(true);
    try {
      await simulateHere(kind, smallBox(result.bbox));
    } catch {
      setBusy(false);
      return;
    }
    setBusy(false);
  }

  return (
    <div className="mt-2.5 rounded-xl bg-raised/70 ring-1 ring-line px-3 py-2.5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[11px] text-dim truncate">{result.display_name}</span>
        <span className="font-mono text-[10px] text-dim shrink-0">
          {Math.round(result.confidence * 100)}% {t("confidence")}
        </span>
      </div>
      <div className="mt-0.5 font-display text-lg text-teal">
        {hs.value.toLocaleString()} <span className="text-sm text-ink/80">{hs.unit}</span>
        <span className="ml-2 text-xs text-dim font-sans">{hs.label}</span>
      </div>
      <div className="mt-1 font-mono text-[10px] text-dim">
        {t("radarDate")} {result.data_date}
      </div>
      {kind && result.mode !== "simulated" && (
        <button
          onClick={simulate}
          disabled={busy || simStatus === "running"}
          className="mt-2 inline-flex items-center gap-1.5 h-7 px-2.5 rounded-lg bg-bg/70 ring-1 ring-line text-[11px] text-ink hover:ring-teal/60 transition disabled:opacity-50"
        >
          {kind === "flood" ? (
            <Waves size={12} className="text-teal" />
          ) : (
            <Flame size={12} className="text-amber" />
          )}
          {busy ? t("simulating") : kind === "flood" ? t("simulateHere") : t("simulateFire")}
        </button>
      )}
    </div>
  );
}

function Bubble({ m }: { m: ChatMessage }) {
  const t = useT();
  const [showWhy, setShowWhy] = useState(false);

  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed bg-raised text-ink">
          {m.text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start" aria-live={m.pending ? "polite" : undefined}>
      <div
        className={`max-w-[92%] rounded-xl px-3.5 py-2.5 ${
          m.pending
            ? "relative overflow-hidden scanline bg-bg/80 text-teal ring-1 ring-teal/30 font-mono text-xs"
            : m.error
              ? "bg-bg/80 text-ink ring-1 ring-amber/40 text-sm"
              : "bg-bg/80 text-ink ring-1 ring-line"
        }`}
      >
        {m.pending || m.error ? m.text : <Markdown text={m.text} />}
        {m.results?.map((r, i) => <ResultCard key={i} result={r} />)}
        {m.reasoning && (
          <div className="mt-2">
            <button
              onClick={() => setShowWhy((v) => !v)}
              aria-expanded={showWhy}
              className="inline-flex items-center gap-1 text-[11px] text-dim hover:text-ink transition"
            >
              <ChevronDown size={12} className={`transition-transform ${showWhy ? "rotate-180" : ""}`} />
              {t("whyThis")}
            </button>
            {showWhy && <p className="mt-1 text-[11px] text-dim leading-relaxed">{m.reasoning}</p>}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatMessages() {
  const t = useT();
  const messages = useChatStore((s) => s.messages);
  const panelOpen = useChatStore((s) => s.panelOpen);
  const setPanelOpen = useChatStore((s) => s.setPanelOpen);
  const loading = useChatStore((s) => s.loading);
  const clear = useChatStore((s) => s.clear);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (!panelOpen || messages.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      role="log"
      aria-label={t("conversation")}
      className="w-full max-w-2xl max-h-[min(22rem,36vh)] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-3 pointer-events-auto"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
          Kairos · {t("conversation")}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={clear}
            disabled={loading}
            className="text-dim hover:text-ink transition-colors disabled:opacity-40"
            title={t("newChat")}
            aria-label={t("newChat")}
          >
            <RotateCcw size={13} />
          </button>
          <button
            onClick={() => setPanelOpen(false)}
            className="text-dim hover:text-ink transition-colors"
            title={t("hideConversation")}
            aria-label={t("hideConversation")}
          >
            <X size={14} />
          </button>
        </div>
      </div>
      {messages.map((m) => (
        <Bubble key={m.id} m={m} />
      ))}
      <div ref={endRef} />
    </motion.div>
  );
}
