import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  Download,
  FileSpreadsheet,
  Loader2,
  Play,
  Upload,
  X,
} from "lucide-react";
import { fetchRegistry } from "../../api/registry";
import { useMapStore } from "../../stores/mapStore";
import {
  BATCH_TEMPLATE,
  batchResultsToCsv,
  parseBatchCsv,
  runBatch,
  type BatchRow,
} from "../../lib/batch";

const STATUS_STYLE: Record<string, string> = {
  pending: "text-dim",
  running: "text-amber",
  ok: "text-teal",
  no_data: "text-dim",
  error: "text-amber",
};

export default function BatchPanel({ onClose }: { onClose: () => void }) {
  const [text, setText] = useState("");
  const [rows, setRows] = useState<BatchRow[]>([]);
  const [parseErrors, setParseErrors] = useState<string[]>([]);
  const [running, setRunning] = useState(false);

  const { data: registry } = useQuery({
    queryKey: ["registry"],
    queryFn: fetchRegistry,
    staleTime: Infinity,
  });
  const validTypes = useMemo(
    () => new Set((registry ?? []).map((r) => r.id)),
    [registry]
  );

  const done = rows.filter((r) => r.status !== "pending" && r.status !== "running");
  const okCount = rows.filter((r) => r.status === "ok").length;

  function loadFromText(raw: string) {
    setText(raw);
    const { inputs, errors } = parseBatchCsv(raw);
    const extra = inputs
      .filter((i) => validTypes.size > 0 && !validTypes.has(i.analysis_type))
      .map((i) => `Unknown analysis_type "${i.analysis_type}" for ${i.label}.`);
    setParseErrors([...errors, ...extra]);
    setRows(
      inputs.map((input, idx) => ({ id: idx, input, status: "pending" as const }))
    );
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    loadFromText(await file.text());
    e.target.value = "";
  }

  async function run() {
    if (!rows.length || running) return;
    setRunning(true);
    try {
      await runBatch(rows, (next) => setRows(next), 3);
    } finally {
      setRunning(false);
    }
  }

  function downloadResults() {
    const blob = new Blob([batchResultsToCsv(rows)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kairos-batch-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function viewRow(r: BatchRow) {
    if (r.status !== "ok" || !r.tileUrl) return;
    const map = useMapStore.getState();
    map.addRasterLayer({
      id: `batch-${r.id}-${Date.now()}`,
      name: `${r.input.label} · ${r.dataDate}`,
      tileUrl: r.tileUrl,
      opacity: 0.85,
      visible: true,
      color: "#00BFA8",
    });
    map.setLastResult({
      analysisType: r.input.analysis_type,
      displayName: r.input.label,
      bbox: r.input.bbox,
      startDate: r.input.start_date,
      endDate: r.input.end_date,
      dataDate: r.dataDate ?? "",
      confidence: r.confidence ?? 0.8,
      headlineLabel: r.headlineLabel ?? "Result",
      headlineValue: r.headlineValue ?? 0,
      headlineUnit: r.headlineUnit ?? "",
    });
    const [a, b, c, d] = r.input.bbox;
    map.requestFlyTo([(a + c) / 2, (b + d) / 2], 7);
  }

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[58dvh] sm:right-20 sm:top-1/2 sm:-translate-y-1/2 sm:w-96 sm:max-h-[82vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-3"
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-dim">
          <FileSpreadsheet size={12} /> BATCH MODE
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      <p className="text-[11px] text-dim leading-relaxed">
        Paste or upload a CSV of sites and date windows. Columns:{" "}
        <span className="font-mono text-[10px] text-teal">
          analysis_type, min_lon, min_lat, max_lon, max_lat, start_date, end_date
        </span>{" "}
        (plus optional <span className="font-mono text-[10px]">label</span>).
      </p>

      <textarea
        value={text}
        onChange={(e) => loadFromText(e.target.value)}
        spellCheck={false}
        placeholder={BATCH_TEMPLATE}
        className="w-full h-28 rounded-xl bg-bg/70 ring-1 ring-line p-2.5 font-mono text-[10px] text-ink placeholder:text-dim/50 resize-none focus:outline-none focus:ring-teal/40"
      />

      <div className="flex items-center gap-2">
        <label className="flex-1 h-8 rounded-lg text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition cursor-pointer">
          <Upload size={12} /> Upload CSV
          <input type="file" accept=".csv,text/csv" onChange={onFile} className="hidden" />
        </label>
        <button
          onClick={() => loadFromText(BATCH_TEMPLATE)}
          className="flex-1 h-8 rounded-lg text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition"
        >
          Load example
        </button>
      </div>

      {parseErrors.length > 0 && (
        <div className="rounded-lg bg-bg/70 ring-1 ring-amber/30 p-2 space-y-0.5 max-h-20 overflow-y-auto">
          {parseErrors.map((e, i) => (
            <p key={i} className="text-[10px] text-amber leading-snug">
              {e}
            </p>
          ))}
        </div>
      )}

      {rows.length > 0 && (
        <>
          <div className="flex items-center gap-2">
            <button
              onClick={run}
              disabled={running}
              className="flex-1 h-9 rounded-xl text-xs flex items-center justify-center gap-1.5 bg-amber text-bg font-medium hover:brightness-110 transition disabled:opacity-60"
            >
              {running ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Play size={13} />
              )}
              {running
                ? `Running ${done.length}/${rows.length}…`
                : `Run ${rows.length} ${rows.length === 1 ? "site" : "sites"}`}
            </button>
            <button
              onClick={downloadResults}
              disabled={okCount === 0 && done.length === 0}
              title="Download results as CSV"
              className="h-9 px-3 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition disabled:opacity-50"
            >
              <Download size={13} /> CSV
            </button>
          </div>

          <ul className="space-y-1.5 max-h-60 overflow-y-auto">
            {rows.map((r) => (
              <li
                key={r.id}
                onClick={() => viewRow(r)}
                className={`rounded-lg bg-bg/70 ring-1 ring-line p-2.5 ${
                  r.status === "ok" ? "cursor-pointer hover:ring-teal/40" : ""
                }`}
                title={r.status === "ok" ? "Click to view on the globe" : r.error}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] text-ink truncate">
                    {r.input.label}
                  </span>
                  <span
                    className={`font-mono text-[9px] uppercase tracking-wider shrink-0 ${
                      STATUS_STYLE[r.status] ?? "text-dim"
                    }`}
                  >
                    {r.status === "running" ? (
                      <Loader2 size={10} className="inline animate-spin" />
                    ) : (
                      r.status.replace("_", " ")
                    )}
                  </span>
                </div>
                <div className="font-mono text-[9px] text-dim mt-0.5 truncate">
                  {r.input.analysis_type}
                  {r.status === "ok" &&
                    ` · ${r.headlineValue?.toLocaleString()} ${r.headlineUnit} · ${r.dataDate}`}
                  {r.status === "no_data" && " · no data in window"}
                  {r.status === "error" && ` · ${r.error}`}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </motion.aside>
  );
}
