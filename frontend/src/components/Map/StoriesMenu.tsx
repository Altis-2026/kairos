import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Loader2, X } from "lucide-react";
import { fetchFeatured, type FeaturedStory } from "../../api/featured";

export function useFeaturedStories() {
  return useQuery({ queryKey: ["featured"], queryFn: fetchFeatured, staleTime: 30 * 60 * 1000 });
}

export default function StoriesMenu({
  onPick,
  onClose,
}: {
  onPick: (story: FeaturedStory) => void;
  onClose: () => void;
}) {
  const { data, isLoading, isError } = useFeaturedStories();
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -8 }}
      role="dialog"
      aria-label="Featured stories"
      className="absolute left-[4.25rem] lg:left-[4.5rem] top-20 lg:top-1/2 lg:-translate-y-1/2 z-40 w-[min(20rem,calc(100vw-6rem))] max-h-[70vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-3"
    >
      <div className="flex items-center justify-between px-1 pb-2">
        <span className="font-mono text-[10px] tracking-[0.22em] text-amber uppercase">Featured stories</span>
        <button onClick={onClose} aria-label="Close" className="text-dim hover:text-ink">
          <X size={14} />
        </button>
      </div>
      {isLoading && (
        <div className="flex items-center gap-2 px-1 py-3 text-xs text-dim">
          <Loader2 size={13} className="animate-spin" /> Loading stories…
        </div>
      )}
      {isError && (
        <p className="px-1 py-3 text-xs text-dim">Stories need the Kairos server. Try again in a moment.</p>
      )}
      <ul className="space-y-1.5">
        {data?.stories.map((s) => (
          <li key={s.id}>
            <button
              onClick={() => onPick(s)}
              className="w-full text-left rounded-xl px-3 py-2.5 ring-1 ring-line hover:ring-teal/50 hover:bg-raised/60 transition"
            >
              <div className="text-sm text-ink">{s.title}</div>
              <div className="text-[11px] text-dim">
                {s.place} · {s.when}
              </div>
            </button>
          </li>
        ))}
      </ul>
    </motion.div>
  );
}
