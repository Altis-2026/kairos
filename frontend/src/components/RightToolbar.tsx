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
  Radar,
  Ship,
  Telescope,
  Waves,
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
import InsarPanel from "./Panels/InsarPanel";
import VesselPanel from "./Panels/VesselPanel";
import SimulationPanel from "./Panels/SimulationPanel";
import PanelErrorBoundary from "./ErrorBoundary";

type PanelKey =
  | "layers"
  | "analytics"
  | "research"
  | "history"
  | "batch"
  | "alerts"
  | "janus"
  | "insar"
  | "vessels"
  | "simulation";

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
  tour,
  active,
  amber,
  onClick,
  children,
}: {
  title: string;
  /** Stable hook for the guided tour; see components/Tutorial. */
  tour?: string;
  active?: boolean;
  amber?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      title={title}
      data-tour={tour}
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
      "insar",
      "vessels",
      // Was missing: a requestPanel("simulation") fell through this list and
      // silently did nothing, so the guide's "Try it" for the forward models
      // opened no panel at all.
      "simulation",
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
      key: "vessels",
      label: "Dark vessels",
      icon: Ship,
      active: openPanel === "vessels",
      onClick: () => openPanelAndCloseSheet("vessels"),
    },
    {
      key: "simulation",
      label: "Forward simulation",
      icon: Waves,
      active: openPanel === "simulation",
      amber: true,
      onClick: () => openPanelAndCloseSheet("simulation"),
    },
    {
      key: "insar",
      label: "InSAR deep dive",
      icon: Radar,
      active: openPanel === "insar",
      onClick: () => openPanelAndCloseSheet("insar"),
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
              tour={`tool-${a.key}`}
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

      {/* Each panel is wrapped individually: a crash in one must never
          take the rest of the app down with it — see ErrorBoundary.tsx. */}
      {openPanel === "simulation" && (
        <PanelErrorBoundary label="Forward simulation" onDismiss={() => setOpenPanel(null)}>
          <SimulationPanel onClose={() => setOpenPanel(null)} />
        </PanelErrorBoundary>
      )}
      {openPanel === "layers" && (
        <PanelErrorBoundary label="Layers" onDismiss={() => setOpenPanel(null)}>
          <LayerPanel onClose={() => setOpenPanel(null)} />
        </PanelErrorBoundary>
      )}
      {openPanel === "research" && (
        <PanelErrorBoundary label="Research tools" onDismiss={() => setOpenPanel(null)}>
          <ResearchPanel onClose={() => setOpenPanel(null)} />
        </PanelErrorBoundary>
      )}
      {openPanel === "history" && (
        <PanelErrorBoundary label="My analyses" onDismiss={() => setOpenPanel(null)}>
          <HistoryPanel onClose={() => setOpenPanel(null)} />
        </PanelErrorBoundary>
      )}
      {openPanel === "batch" && (
        <PanelErrorBoundary label="Batch mode" onDismiss={() => setOpenPanel(null)}>
          <BatchPanel onClose={() => setOpenPanel(null)} />
        </PanelErrorBoundary>
      )}
      {openPanel === "alerts" && (
        <PanelErrorBoundary label="Alerts" onDismiss={() => setOpenPanel(null)}>
          <AlertsPanel onClose={() => setOpenPanel(null)} />
        </PanelErrorBoundary>
      )}
      {openPanel === "analytics" && (
        <PanelErrorBoundary label="Analytics" onDismiss={() => setOpenPanel(null)}>
          <AnalyticsPanel onClose={() => setOpenPanel(null)} />
        </PanelErrorBoundary>
      )}
      {openPanel === "janus" && (
        <PanelErrorBoundary label="Janus" onDismiss={() => setOpenPanel(null)}>
          <JanusPanel onClose={() => setOpenPanel(null)} />
        </PanelErrorBoundary>
      )}
      {openPanel === "vessels" && (
        <PanelErrorBoundary label="Dark vessels" onDismiss={() => setOpenPanel(null)}>
          <VesselPanel onClose={() => setOpenPanel(null)} />
        </PanelErrorBoundary>
      )}
      {openPanel === "insar" && (
        <PanelErrorBoundary label="InSAR" onDismiss={() => setOpenPanel(null)}>
          <InsarPanel onClose={() => setOpenPanel(null)} />
        </PanelErrorBoundary>
      )}
    </>
  );
}
