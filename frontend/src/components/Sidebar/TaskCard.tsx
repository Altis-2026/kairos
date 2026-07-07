import {
  Waves,
  Ship,
  Flame,
  Droplets,
  Trees,
  Snowflake,
  Activity,
  Building,
  Building2,
  TrendingDown,
  Sprout,
  Pickaxe,
  type LucideIcon,
} from "lucide-react";
import type { AnalysisType } from "../../types/analysis";

const ICONS: Record<string, LucideIcon> = {
  waves: Waves,
  ship: Ship,
  flame: Flame,
  droplets: Droplets,
  trees: Trees,
  snowflake: Snowflake,
  activity: Activity,
  building: Building,
  "building-2": Building2,
  "trending-down": TrendingDown,
  sprout: Sprout,
  pickaxe: Pickaxe,
};

export default function TaskCard({
  task,
  onSelect,
}: {
  task: AnalysisType;
  onSelect: () => void;
}) {
  const Icon = ICONS[task.icon] ?? Waves;
  return (
    <button
      onClick={onSelect}
      className="w-full text-left rounded-xl bg-bg/70 ring-1 ring-line hover:ring-teal/50 p-3.5 transition-colors group"
    >
      <div className="flex items-start gap-3">
        <span
          className="h-9 w-9 shrink-0 grid place-items-center rounded-lg ring-1 ring-line group-hover:ring-teal/40 transition-colors"
          style={{ color: task.color_palette[0] }}
        >
          <Icon size={17} />
        </span>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm text-ink font-medium truncate">
              {task.display_name}
            </span>
            {task.data_sources.map((d) => (
              <span
                key={d}
                className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-raised text-dim ring-1 ring-line"
              >
                {d}
              </span>
            ))}
          </div>
          <p className="mt-1 text-xs text-dim leading-relaxed line-clamp-2">
            {task.description}
          </p>
          <p className="mt-1.5 font-mono text-[10px] text-dim/80">
            ~{task.estimated_seconds}s typical run
          </p>
        </div>
      </div>
    </button>
  );
}
