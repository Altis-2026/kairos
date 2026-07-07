import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { X } from "lucide-react";
import { useMapStore } from "../../stores/mapStore";

export default function CompareSlider() {
  const compare = useMapStore((s) => s.compare);
  const setLayerOpacity = useMapStore((s) => s.setLayerOpacity);
  const [value, setValue] = useState(0.5);

  useEffect(() => {
    if (compare) setLayerOpacity(compare.afterLayerId, value);
  }, [value, compare, setLayerOpacity]);

  if (!compare) return null;

  function close() {
    const map = useMapStore.getState();
    map.clearGroup("compare");
    map.setCompare(null);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      className="absolute top-20 left-1/2 -translate-x-1/2 z-30 w-[440px] max-w-[90vw] rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel px-4 py-3 pointer-events-auto"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
          BEFORE / AFTER
        </span>
        <button onClick={close} className="text-dim hover:text-ink" title="Close comparison">
          <X size={14} />
        </button>
      </div>
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={value}
        onChange={(e) => setValue(Number(e.target.value))}
        className="w-full accent-teal h-1"
      />
      <div className="mt-2 flex items-center justify-between font-mono text-[10px]">
        <span className={value < 0.5 ? "text-teal" : "text-dim"}>
          {compare.beforeLabel}
        </span>
        <span className={value >= 0.5 ? "text-teal" : "text-dim"}>
          {compare.afterLabel}
        </span>
      </div>
    </motion.div>
  );
}
