/** Layer management: visibility, opacity, removal, base style. */
import { Eye, EyeOff, Trash2, X } from "lucide-react";
import { motion } from "framer-motion";
import { useMapStore } from "../../stores/mapStore";

export default function LayerPanel({ onClose }: { onClose: () => void }) {
  const layers = useMapStore((s) => s.layers);
  const baseStyle = useMapStore((s) => s.baseStyle);
  const setBaseStyle = useMapStore((s) => s.setBaseStyle);
  const toggleLayerVisible = useMapStore((s) => s.toggleLayerVisible);
  const setLayerOpacity = useMapStore((s) => s.setLayerOpacity);
  const removeLayer = useMapStore((s) => s.removeLayer);

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute right-20 top-1/2 -translate-y-1/2 z-30 w-80 rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
          LAYERS
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      {/* Base style */}
      <div className="flex gap-2">
        {(["satellite", "dark"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setBaseStyle(s)}
            className={`flex-1 h-9 rounded-lg text-xs capitalize transition ring-1 ${
              baseStyle === s
                ? "bg-raised text-teal ring-teal/50"
                : "text-dim ring-line hover:text-ink"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Analysis layers */}
      {layers.length === 0 ? (
        <p className="text-xs text-dim leading-relaxed">
          No analysis layers yet. Run an analysis from the sidebar or ask a
          question below — results appear here.
        </p>
      ) : (
        <ul className="space-y-3 max-h-72 overflow-y-auto">
          {layers.map((l) => (
            <li key={l.id} className="rounded-xl bg-bg/70 ring-1 ring-line p-3 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 text-xs text-ink truncate">
                  <span
                    className="h-2 w-2 rounded-full shrink-0"
                    style={{ background: l.color }}
                  />
                  {l.name}
                </span>
                <div className="flex items-center gap-1.5 shrink-0">
                  <button
                    onClick={() => toggleLayerVisible(l.id)}
                    className="text-dim hover:text-ink"
                    title={l.visible ? "Hide layer" : "Show layer"}
                  >
                    {l.visible ? <Eye size={14} /> : <EyeOff size={14} />}
                  </button>
                  <button
                    onClick={() => removeLayer(l.id)}
                    className="text-dim hover:text-ink"
                    title="Remove layer"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={l.opacity}
                onChange={(e) => setLayerOpacity(l.id, Number(e.target.value))}
                className="w-full accent-teal h-1"
                title="Layer opacity"
              />
            </li>
          ))}
        </ul>
      )}
    </motion.aside>
  );
}
