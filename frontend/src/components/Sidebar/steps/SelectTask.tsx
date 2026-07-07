import { useQuery } from "@tanstack/react-query";
import { fetchRegistry } from "../../../api/registry";
import { useSidebarStore } from "../../../stores/sidebarStore";
import TaskCard from "../TaskCard";
import type { AnalysisType } from "../../../types/analysis";

export default function SelectTask() {
  const selectTask = useSidebarStore((s) => s.selectTask);
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["registry"],
    queryFn: fetchRegistry,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="relative overflow-hidden scanline rounded-xl bg-bg/70 ring-1 ring-teal/20 p-4">
        <p className="font-mono text-xs text-teal">Loading analysis registry…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl bg-bg/70 ring-1 ring-line p-4 space-y-3">
        <p className="text-xs text-dim leading-relaxed">
          Can't reach the Kairos API.{" "}
          {error instanceof Error ? error.message : ""} Check that the backend
          is running on port 8000, then try again.
        </p>
        <button
          onClick={() => refetch()}
          className="h-8 px-3 rounded-lg bg-raised text-xs text-ink ring-1 ring-line hover:ring-teal/50 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  const tasks = data ?? [];
  const categories = [...new Set(tasks.map((t) => t.category))];

  return (
    <div className="space-y-5">
      <p className="text-xs text-dim leading-relaxed">
        Choose what to look for. Every analysis runs on Sentinel-1 radar, which
        sees through clouds, smoke, and darkness.
      </p>
      {categories.map((cat) => (
        <div key={cat} className="space-y-2">
          <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
            {cat}
          </h3>
          {tasks
            .filter((t) => t.category === cat)
            .map((t: AnalysisType) => (
              <TaskCard key={t.id} task={t} onSelect={() => selectTask(t)} />
            ))}
        </div>
      ))}
    </div>
  );
}
