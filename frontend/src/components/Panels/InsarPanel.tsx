import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, Layers, Loader2, Radar, X } from "lucide-react";
import { useMapStore, bboxCenterZoom } from "../../stores/mapStore";
import { fetchInsarSites, insarLayerUrl, type InsarSite } from "../../api/insar";

const IFG_ID = "insar-interferogram";
const COH_ID = "insar-coherence";

export default function InsarPanel({ onClose }: { onClose: () => void }) {
  const [sites, setSites] = useState<InsarSite[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const imageLayers = useMapStore((s) => s.imageLayers);

  useEffect(() => {
    fetchInsarSites()
      .then((d) => setSites(d.sites))
      .catch(() => setError("Could not reach the InSAR service."));
  }, []);

  const ifgOn = imageLayers.some((l) => l.id === IFG_ID);
  const cohOn = imageLayers.some((l) => l.id === COH_ID);

  function toggle(site: InsarSite, kind: "interferogram" | "coherence") {
    const map = useMapStore.getState();
    const id = kind === "interferogram" ? IFG_ID : COH_ID;
    const on = map.imageLayers.some((l) => l.id === id);
    if (on) {
      map.removeLayer(id);
      return;
    }
    const path = site.layers[kind];
    if (!path) return;
    map.removeLayer(kind === "interferogram" ? COH_ID : IFG_ID);
    map.addImageLayer({
      id,
      name: `${site.name} ${kind}`,
      url: insarLayerUrl(path),
      bbox: site.bbox,
      opacity: 0.9,
      visible: true,
    });
    const { center, zoom } = bboxCenterZoom(site.bbox);
    map.requestFlyTo(center, zoom);
  }

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[62dvh] sm:right-20 sm:top-1/2 sm:-translate-y-1/2 sm:w-[22rem] sm:max-h-[84vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-dim">
          <Radar size={13} className="text-teal" /> INSAR DEEP DIVE
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      <p className="text-xs text-dim leading-relaxed">
        The rest of Kairos measures radar brightness. Interferometry measures
        the radar's phase, the shift between two passes, which reveals ground
        movement down to centimetres. This runs on published research-grade
        products, not on Kairos's own pipeline.
      </p>

      {error ? (
        <p className="text-[11px] text-amber leading-snug">{error}</p>
      ) : !sites ? (
        <div className="flex items-center gap-2 text-xs text-dim">
          <Loader2 size={14} className="animate-spin" /> Loading sites…
        </div>
      ) : (
        sites.map((site) => (
          <div key={site.id} className="rounded-xl bg-bg/70 ring-1 ring-line p-3 space-y-2.5">
            <div>
              <div className="text-sm text-ink font-medium">{site.name}</div>
              <div className="font-mono text-[10px] text-dim mt-0.5">
                {site.dates
                  ? `${site.dates[0]} → ${site.dates[1]}`
                  : "date pair on install"}
                {site.frame && ` · frame ${site.frame}`}
              </div>
            </div>
            <p className="text-[11px] text-dim leading-relaxed">{site.description}</p>

            {site.available ? (
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => toggle(site, "interferogram")}
                  className={`h-9 rounded-lg text-[11px] flex items-center justify-center gap-1.5 ring-1 transition ${
                    ifgOn
                      ? "bg-raised text-teal ring-teal/50"
                      : "text-dim ring-line hover:text-ink"
                  }`}
                >
                  <Layers size={12} /> Interferogram
                </button>
                <button
                  onClick={() => toggle(site, "coherence")}
                  className={`h-9 rounded-lg text-[11px] flex items-center justify-center gap-1.5 ring-1 transition ${
                    cohOn
                      ? "bg-raised text-teal ring-teal/50"
                      : "text-dim ring-line hover:text-ink"
                  }`}
                >
                  <Layers size={12} /> Coherence
                </button>
              </div>
            ) : (
              <p className="text-[10px] text-amber leading-snug rounded-lg bg-bg ring-1 ring-line p-2">
                Dataset not installed on this server. Run{" "}
                <span className="font-mono">tools/get_insar_demo.py</span> to
                download the LiCSAR product.
              </p>
            )}

            <div className="rounded-lg bg-bg ring-1 ring-line p-2 space-y-1">
              <div className="font-mono text-[9px] tracking-wider text-dim">
                ONE FRINGE ≈ 2.8 CM OF MOTION
              </div>
              <a
                href={site.source_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-[10px] text-teal hover:underline"
              >
                Source: {site.source} <ExternalLink size={9} />
              </a>
            </div>
          </div>
        ))
      )}
    </motion.aside>
  );
}
