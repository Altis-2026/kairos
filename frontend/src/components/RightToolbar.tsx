/**
 * Right-side controls: analytics, globe view, layers, zoom, locate.
 *
 * Below `lg` (1024px) there is nowhere to float a 12-button vertical rail
 * without it running off the top or bottom of the screen, so it collapses to
 * a single "Tools" launcher that opens a full-width bottom sheet grid instead.
 * Both renderings are driven by the same action list, so behavior never
 * drifts between the two.
 */
import {
  BarChart3,
  Bell,
  FileSpreadsheet,
  FlaskConical,
  Globe2,
  Grid3x3,
  History,
  Layers,
  LocateFixed,
  Map as MapIcon,
  Minus,
  Plus,
  Telescope,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useMapStore } from "../stores/mapStore";
import { useIsCompact } from "../hooks/useIsCompact";
import LayerPanel from "./Panels/LayerPanel";
import AnalyticsPanel from "./Panels/AnalyticsPanel";
import ResearchPanel from "./Panels/ResearchPanel";
import HistoryPanel from "./Panels/HistoryPanel";
import BatchPanel from "./Panels/BatchPanel";
import AlertsPanel from "./Panels/AlertsPanel";
import JanusPanel from "./Janus/JanusPanel";

type PanelKey =
  | "layers"
  | "analytics"
  | "research"
  | "history"
  | "batch"
  | "alerts"
  | "janus";

interface ToolAction {
  key: string;
  label: string;
  icon: LucideIcon;
  active?: boolean;
  amber?: boolean;
  onClick: () => void;
}

function ToolButton({
  title,
  active,
  amber,
  onClick,
  children,
}: {
  title: string;
  active?: boolean;
  amber?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      title={title}
      onClick={onClick}
      className={`h-10 w-10 grid place-items-center transition-colors ${
        active ? (amber ? "text-amber" : "text-teal") : "text-dim hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

export default function RightToolbar() {
  const [openPanel, setOpenPanel] = useState<PanelKey | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const isCompact = useIsCompact();
  const requestFlyTo = useMapStore((s) => s.requestFlyTo);
  const projection = useMapStore((s) => s.projection);
  const toggleProjection = useMapStore((s) => s.toggleProjection);
  const panelRequest = useMapStore((s) => s.panelRequest);
  const clearPanelRequest = useMapStore((s) => s.clearPanelRequest);

  // The tutorial's "Try it" buttons ask us to open a specific panel.
  useEffect(() => {
    if (!panelRequest) return;
    const known: PanelKey[] = [
      "layers",
      "analytics",
      "research",
      "history",
      "batch",
      "alerts",
      "janus",
    ];
    if ((known as string[]).includes(panelRequest)) {
      setOpenPanel(panelRequest as PanelKey);
    }
    clearPanelRequest();
  }, [panelRequest, clearPanelRequest]);

  const zoomBy = (delta: number) => {
    // Globe listens to flyTo; for zoom buttons we nudge using current viewport
    const vb = useMapStore.getState().viewportBbox;
    const center: [number, number] = vb
      ? [(vb[0] + vb[2]) / 2, (vb[1] + vb[3]) / 2]
      : [25, 18];
    const span = vb ? Math.max(vb[2] - vb[0], vb[3] - vb[1]) : 90;
    const approxZoom = Math.log2(360 / Math.max(span, 0.01));
    requestFlyTo(center, Math.min(15, Math.max(1.5, approxZoom + delta)));
  };

  function openPanelAndCloseSheet(key: PanelKey) {
    setOpenPanel(openPanel === key ? null : key);
    setSheetOpen(false);
  }
  function runAndCloseSheet(fn: () => void) {
    fn();
    setSheetOpen(false);
  }

  const actions: ToolAction[] = [
    {
      key: "janus",
      label: "Janus mentor",
      icon: Telescope,
      active: openPanel === "janus",
      amber: true,
      onClick: () => openPanelAndCloseSheet("janus"),
    },
    {
      key: "analytics",
      label: "Analytics",
      icon: BarChart3,
      active: openPanel === "analytics",
      onClick: () => openPanelAndCloseSheet("analytics"),
    },
    {
      key: "reset-view",
      label: "Reset globe view",
      icon: Globe2,
      onClick: () => runAndCloseSheet(() => requestFlyTo([25, 18], 2.1)),
    },
    {
      key: "projection",
      label: projection === "globe" ? "Switch to 2D flat map" : "Switch to 3D globe",
      icon: projection === "globe" ? MapIcon : Globe2,
      active: projection === "mercator",
      onClick: () => runAndCloseSheet(toggleProjection),
    },
    {
      key: "layers",
      label: "Layers",
      icon: Layers,
      active: openPanel === "layers",
      onClick: () => openPanelAndCloseSheet("layers"),
    },
    {
      key: "research",
      label: "Research tools",
      icon: FlaskConical,
      active: openPanel === "research",
      onClick: () => openPanelAndCloseSheet("research"),
    },
    {
      key: "history",
      label: "My analyses",
      icon: History,
      active: openPanel === "history",
      onClick: () => openPanelAndCloseSheet("history"),
    },
    {
      key: "batch",
      label: "Batch mode (CSV)",
      icon: FileSpreadsheet,
      active: openPanel === "batch",
      onClick: () => openPanelAndCloseSheet("batch"),
    },
    {
      key: "alerts",
      label: "Alerts",
      icon: Bell,
      active: openPanel === "alerts",
      onClick: () => openPanelAndCloseSheet("alerts"),
    },
    {
      key: "zoom-in",
      label: "Zoom in",
      icon: Plus,
      onClick: () => runAndCloseSheet(() => zoomBy(1)),
    },
    {
      key: "zoom-out",
      label: "Zoom out",
      icon: Minus,
      onClick: () => runAndCloseSheet(() => zoomBy(-1)),
    },
    {
      key: "locate",
      label: "My location",
      icon: LocateFixed,
      onClick: () =>
        runAndCloseSheet(() => {
          navigator.geolocation?.getCurrentPosition((pos) =>
            requestFlyTo([pos.coords.longitude, pos.coords.latitude], 9)
          );
        }),
    },
  ];

  return (
    <>
      {isCompact ? (
        <button
          title="Tools"
          onClick={() => setSheetOpen(true)}
          className="absolute right-5 top-1/2 -translate-y-1/2 z-30 h-12 w-12 grid place-items-center rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel text-dim hover:text-ink transition-colors"
        >
          <Grid3x3 size={19} />
        </button>
      ) : (
        <div className="absolute right-5 top-1/2 -translate-y-1/2 z-30 flex flex-col items-center rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel divide-y divide-line">
          {actions.map((a) => (
            <ToolButton
              key={a.key}
              title={a.label}
              active={a.active}
              amber={a.amber}
              onClick={a.onClick}
            >
              <a.icon size={17} />
            </ToolButton>
          ))}
        </div>
      )}

      <AnimatePresence>
        {isCompact && sheetOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-40 bg-bg/60 backdrop-blur-sm"
            onClick={() => setSheetOpen(false)}
          >
            <motion.div
              initial={{ y: 60, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 60, opacity: 0 }}
              transition={{ type: "spring", stiffness: 320, damping: 32 }}
              onClick={(e) => e.stopPropagation()}
              className="absolute inset-x-3 bottom-3 max-h-[70vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="font-mono text-[10px] tracking-[0.22em] text-dim">
                  TOOLS
                </span>
                <button
                  onClick={() => setSheetOpen(false)}
                  className="text-dim hover:text-ink transition-colors"
                  title="Close"
                >
                  <X size={16} />
                </button>
              </div>
              <div className="grid grid-cols-4 gap-2.5">
                {actions.map((a) => (
                  <button
                    key={a.key}
                    onClick={a.onClick}
                    className={`flex flex-col items-center gap-1.5 rounded-xl ring-1 py-3 px-1.5 text-center transition-colors ${
                      a.active
                        ? a.amber
                          ? "text-amber ring-amber/40 bg-amber/10"
                          : "text-teal ring-teal/40 bg-teal/10"
                        : "text-dim ring-line hover:text-ink"
                    }`}
                  >
                    <a.icon size={19} />
                    <span className="text-[9px] leading-tight">{a.label}</span>
                  </button>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {openPanel === "layers" && <LayerPanel onClose={() => setOpenPanel(null)} />}
      {openPanel === "research" && (
        <ResearchPanel onClose={() => setOpenPanel(null)} />
      )}
      {openPanel === "history" && (
        <HistoryPanel onClose={() => setOpenPanel(null)} />
      )}
      {openPanel === "batch" && (
        <BatchPanel onClose={() => setOpenPanel(null)} />
      )}
      {openPanel === "alerts" && (
        <AlertsPanel onClose={() => setOpenPanel(null)} />
      )}
      {openPanel === "analytics" && (
        <AnalyticsPanel onClose={() => setOpenPanel(null)} />
      )}
      {openPanel === "janus" && <JanusPanel onClose={() => setOpenPanel(null)} />}
    </>
  );
}
