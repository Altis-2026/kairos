import { useSidebarStore } from "../../../stores/sidebarStore";

export default function Configure() {
  const startDate = useSidebarStore((s) => s.startDate);
  const endDate = useSidebarStore((s) => s.endDate);
  const setDates = useSidebarStore((s) => s.setDates);
  const confirmConfig = useSidebarStore((s) => s.confirmConfig);
  const selectedTask = useSidebarStore((s) => s.selectedTask);

  const datesValid = startDate < endDate;

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">Analysis period</h3>
        <div className="grid grid-cols-2 gap-2">
          <label className="space-y-1">
            <span className="text-[11px] text-dim">Start</span>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setDates(e.target.value, endDate)}
              className="w-full h-10 px-3 rounded-xl bg-bg/70 ring-1 ring-line text-xs text-ink outline-none focus:ring-teal/50 [color-scheme:dark]"
            />
          </label>
          <label className="space-y-1">
            <span className="text-[11px] text-dim">End</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setDates(startDate, e.target.value)}
              className="w-full h-10 px-3 rounded-xl bg-bg/70 ring-1 ring-line text-xs text-ink outline-none focus:ring-teal/50 [color-scheme:dark]"
            />
          </label>
        </div>
        {!datesValid && <p className="text-[11px] text-amber">Start date must be before end date.</p>}
        <p className="text-[11px] text-dim leading-relaxed">
          Sentinel-1 revisits most places every 12 days. Windows shorter than that may contain no scenes.
        </p>
      </div>

      <div className="rounded-xl bg-bg/70 ring-1 ring-line p-3 space-y-1.5 text-[11px] leading-relaxed">
        <div className="flex justify-between gap-3">
          <span className="text-dim">Baseline</span>
          <span className="text-ink text-right">30 to 365 days before the start date</span>
        </div>
        <div className="flex justify-between gap-3">
          <span className="text-dim">Data source</span>
          <span className="text-ink text-right">Sentinel-1 C-band radar</span>
        </div>
      </div>

      <button
        disabled={!datesValid}
        onClick={confirmConfig}
        className="w-full h-10 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition disabled:opacity-40"
      >
        Check data availability
      </button>

      {selectedTask?.id === "sea_ice" && (
        <p className="text-[11px] text-amber leading-relaxed">
          Sea ice mapping uses polar EW-mode acquisitions. It only returns data above roughly 55° latitude.
        </p>
      )}
    </div>
  );
}
