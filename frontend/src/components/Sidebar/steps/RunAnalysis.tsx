import { useEffect, useRef, useState } from "react";
import { runAnalyze } from "../../../api/analyze";
import { useMapStore } from "../../../stores/mapStore";
import { useSidebarStore } from "../../../stores/sidebarStore";
import { applyResultToGlobe } from "../../Chat/ChatBar";

const STAGES = [
  "Querying Sentinel-1 archive…",
  "Loading radar scenes…",
  "Calibrating backscatter…",
  "Comparing against baseline…",
  "Isolating change signal…",
  "Generating map tiles…",
];

export default function RunAnalysis() {
  const [stageIdx, setStageIdx] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const startedRef = useRef(false);
  const { selectedTask, startDate, endDate, finishRun, failRun } =
    useSidebarStore();
  const aoi = useMapStore((s) => s.aoi);
  const aoiPolygon = useMapStore((s) => s.aoiPolygon);

  useEffect(() => {
    const est = (selectedTask?.estimated_seconds ?? 20) * 1000;
    const perStage = Math.max(1500, est / STAGES.length);
    const stageTimer = setInterval(
      () => setStageIdx((i) => Math.min(i + 1, STAGES.length - 1)),
      perStage
    );
    const clock = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => {
      clearInterval(stageTimer);
      clearInterval(clock);
    };
  }, [selectedTask]);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    if (!selectedTask || !aoi) {
      failRun("Missing task or area. Go back and complete the earlier steps.");
      return;
    }

    runAnalyze({
      analysis_type: selectedTask.id,
      bbox: aoi,
      start_date: startDate,
      end_date: endDate,
      polygon: aoiPolygon,
    })
      .then((result) => {
        applyResultToGlobe(result);
        finishRun(result);
      })
      .catch((e) => {
        failRun(
          e instanceof Error ? e.message : "Analysis failed for an unknown reason."
        );
      });

  }, []);

  return (
    <div className="space-y-4">
      <div className="relative overflow-hidden scanline rounded-xl bg-bg/80 ring-1 ring-teal/30 p-4 space-y-2.5">
        {STAGES.slice(0, stageIdx + 1).map((s, i) => (
          <p
            key={s}
            className={`font-mono text-xs ${
              i === stageIdx ? "text-teal" : "text-dim"
            }`}
          >
            {i < stageIdx ? "✓" : "▸"} {s}
          </p>
        ))}
      </div>
      <div className="flex justify-between font-mono text-[10px] text-dim">
        <span>
          {selectedTask?.display_name} · est ~{selectedTask?.estimated_seconds}s
        </span>
        <span className="text-teal">{elapsed}s</span>
      </div>
      <p className="text-[11px] text-dim leading-relaxed">
        Computation runs on Google Earth Engine. Petabytes stay in the cloud,
        only the result tiles come back.
      </p>
    </div>
  );
}
