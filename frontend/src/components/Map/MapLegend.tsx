import { AnimatePresence, motion } from "framer-motion";
import { useMapStore } from "../../stores/mapStore";

export default function MapLegend() {
  const layers = useMapStore((s) => s.layers);
  const pointLayers = useMapStore((s) => s.pointLayers);

  const entries = [
    ...layers.filter((l) => l.visible).map((l) => ({ id: l.id, name: l.name, color: l.color })),
    ...pointLayers
      .filter((l) => l.visible)
      .map((l) => ({ id: l.id, name: l.name, color: l.color })),
  ];

  return (
    <AnimatePresence>
      {entries.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 8 }}
          className="absolute z-20 max-sm:left-3 max-sm:top-16 sm:left-5 sm:bottom-20 max-w-[16rem] rounded-xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel px-3 py-2.5 pointer-events-none"
        >
          <div className="font-mono text-[9px] tracking-[0.2em] text-dim uppercase mb-1.5">
            On the map
          </div>
          <ul className="space-y-1">
            {entries.map((e) => (
              <li key={e.id} className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-sm shrink-0 ring-1 ring-white/10"
                  style={{ background: e.color }}
                />
                <span className="text-[11px] text-ink/90 truncate">{e.name}</span>
              </li>
            ))}
          </ul>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
