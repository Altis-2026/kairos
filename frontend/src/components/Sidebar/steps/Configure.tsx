import { useSidebarStore } from "../../../stores/sidebarStore";

export default function Configure() {
  const {
    startDate,
    endDate,
    setDates,
    baseline,
    setBaseline,
    dataSource,
    setDataSource,
    confirmConfig,
    selectedTask,
  } = useSidebarStore();

  const datesValid = startDate < endDate;

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
          Analysis period
        </h3>
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
        {!datesValid && (
          <p className="text-[11px] text-amber">Start date must be before end date.</p>
        )}
        <p className="text-[11px] text-dim leading-relaxed">
          Sentinel-1 revisits most places every 12 days. Windows shorter than
          that may contain no scenes.
        </p>
      </div>

      <div className="space-y-2">
        <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
          Baseline
        </h3>
        {(
          [
            ["recent_12m", "Recent history", "30–365 days before the start date (recommended)"],
            ["5y_average", "5-year average", "Same season averaged over five years (coming later)"],
            ["custom", "Custom period", "Pick exact baseline dates (coming later)"],
          ] as const
        ).map(([value, label, hint]) => {
          const disabled = value !== "recent_12m";
          return (
            <label
              key={value}
              className={`flex items-start gap-2.5 rounded-xl p-3 ring-1 transition-colors ${
                baseline === value ? "ring-teal/50 bg-bg/70" : "ring-line"
              } ${disabled ? "opacity-50" : "cursor-pointer hover:ring-teal/30"}`}
            >
              <input
                type="radio"
                name="baseline"
                checked={baseline === value}
                disabled={disabled}
                onChange={() => setBaseline(value)}
                className="mt-0.5 accent-teal"
              />
              <span>
                <span className="block text-xs text-ink">{label}</span>
                <span className="block text-[11px] text-dim">{hint}</span>
              </span>
            </label>
          );
        })}
      </div>

      <div className="space-y-2">
        <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
          Data source
        </h3>
        <div className="flex gap-2">
          {(
            [
              ["sentinel1", "Sentinel-1", false],
              ["alos2", "ALOS-2", true],
              ["auto", "Auto", true],
            ] as const
          ).map(([value, label, disabled]) => (
            <button
              key={value}
              disabled={disabled}
              onClick={() => setDataSource(value)}
              title={disabled ? "Coming in Phase 2" : undefined}
              className={`flex-1 h-9 rounded-xl text-xs ring-1 transition-colors ${
                dataSource === value
                  ? "bg-raised text-teal ring-teal/50"
                  : "text-dim ring-line hover:text-ink"
              } disabled:opacity-40`}
            >
              {label}
            </button>
          ))}
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
          Sea ice mapping uses polar EW-mode acquisitions, so it only returns
          data above roughly 55° latitude.
        </p>
      )}
    </div>
  );
}
