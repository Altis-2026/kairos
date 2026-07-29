import { useQuery } from "@tanstack/react-query";
import { ArrowDownToLine, ArrowUpFromLine, SatelliteDish } from "lucide-react";
import { fetchScenes } from "../../../api/scenes";
import { useMapStore } from "../../../stores/mapStore";
import { useSidebarStore } from "../../../stores/sidebarStore";
import { estimateNextPass } from "../../../lib/nextPass";

export default function PreviewScenes() {
  const aoi = useMapStore((s) => s.aoi);
  const { startDate, endDate, startRun, error } = useSidebarStore();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["scenes", aoi, startDate, endDate],
    queryFn: () => fetchScenes(aoi!, startDate, endDate),
    enabled: !!aoi,
  });

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-xl bg-bg/70 ring-1 ring-amber/40 p-3 text-xs text-amber leading-relaxed">
          {error}
        </div>
      )}

      {isLoading && (
        <div className="relative overflow-hidden scanline rounded-xl bg-bg/70 ring-1 ring-teal/20 p-4">
          <p className="font-mono text-xs text-teal">
            Searching the Sentinel-1 archive…
          </p>
        </div>
      )}

      {isError && (
        <div className="rounded-xl bg-bg/70 ring-1 ring-line p-3 text-xs text-dim leading-relaxed">
          Scene lookup failed. You can still run the analysis; availability is
          re-checked server-side.
        </div>
      )}

      {data && (
        <>
          <div className="rounded-xl bg-bg/70 ring-1 ring-line p-3 flex items-baseline justify-between">
            <span className="text-xs text-dim">Scenes available</span>
            <span className="font-display text-2xl text-teal">
              {data.scene_count}
            </span>
          </div>

          {data.scene_count === 0 && (
            <p className="text-[11px] text-amber leading-relaxed">
              No scenes in this window. Widen the date range, since Sentinel-1
              revisits most places every 12 days.
            </p>
          )}

          {(() => {
            const pass = estimateNextPass(data.scenes.map((s) => s.date));
            if (!pass) return null;
            return (
              <div className="rounded-xl bg-bg/70 ring-1 ring-teal/25 p-3">
                <div className="flex items-center gap-1.5 font-mono text-[9px] tracking-[0.18em] text-teal uppercase">
                  <SatelliteDish size={11} /> Next expected pass
                </div>
                <div className="mt-1 text-xs text-ink">
                  {pass.nextDate}
                  <span className="text-dim">
                    {" "}
                    ({pass.daysAway === 0
                      ? "today"
                      : pass.daysAway === 1
                      ? "tomorrow"
                      : `in ${pass.daysAway} days`})
                  </span>
                </div>
                <div className="mt-0.5 font-mono text-[9px] text-dim">
                  from the {pass.cadenceDays}-day revisit measured here, last
                  seen {pass.lastDate}
                </div>
              </div>
            );
          })()}

          <ul className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
            {data.scenes.map((s) => (
              <li
                key={s.scene_id}
                className="rounded-lg bg-bg/60 ring-1 ring-line px-3 py-2 flex items-center justify-between gap-2"
              >
                <span className="font-mono text-[11px] text-ink">{s.date}</span>
                <span className="flex items-center gap-2 font-mono text-[9px] text-dim">
                  {s.orbit_direction === "ASCENDING" ? (
                    <ArrowUpFromLine size={11} className="text-teal" />
                  ) : (
                    <ArrowDownToLine size={11} className="text-amber" />
                  )}
                  {s.orbit_direction.slice(0, 4)} · {s.instrument_mode} ·{" "}
                  {s.polarizations.join("/")}
                </span>
              </li>
            ))}
          </ul>

          <p className="text-[10px] text-dim leading-relaxed">
            All matching scenes feed the composite. Per-scene exclusion ships in
            a later update.
          </p>
        </>
      )}

      <button
        onClick={startRun}
        disabled={isLoading || (data && data.scene_count === 0)}
        className="w-full h-10 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition disabled:opacity-40"
      >
        Run analysis
      </button>
    </div>
  );
}
