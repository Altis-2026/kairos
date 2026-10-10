import {
  BarChart3,
  Bell,
  Bot,
  FileSpreadsheet,
  FlaskConical,
  Globe2,
  Grid3x3,
  History,
  Home,
  Landmark,
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
import { lazy, Suspense, useEffect, useState, type ComponentType, type LazyExoticComponent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useMapStore } from "../stores/mapStore";
import { useIsCompact } from "../hooks/useIsCompact";
import PanelErrorBoundary from "./ErrorBoundary";

type PanelProps = { onClose: () => void };

const PANELS = {
  myplace: { label: "My Place", component: lazy(() => import("./Panels/MyPlacePanel")) },
  district: { label: "My District", component: lazy(() => import("./Panels/DistrictPanel")) },
  simulation: { label: "Simulate", component: lazy(() => import("./Panels/SimulationPanel")) },
  janus: { label: "Janus mentor", component: lazy(() => import("./Janus/JanusPanel")) },
  agent: { label: "Agent mode", component: lazy(() => import("./Panels/AgentPanel")) },
  layers: { label: "Layers", component: lazy(() => import("./Panels/LayerPanel")) },
  research: { label: "Research tools", component: lazy(() => import("./Panels/ResearchPanel")) },
  analytics: { label: "Analytics", component: lazy(() => import("./Panels/AnalyticsPanel")) },
  history: { label: "My analyses", component: lazy(() => import("./Panels/HistoryPanel")) },
  batch: { label: "Batch analysis", component: lazy(() => import("./Panels/BatchPanel")) },
  alerts: { label: "Alerts", component: lazy(() => import("./Panels/AlertsPanel")) },
  vessels: { label: "Dark vessels", component: lazy(() => import("./Panels/VesselPanel")) },
  insar: { label: "InSAR deep dive", component: lazy(() => import("./Panels/InsarPanel")) },
} satisfies Record<string, { label: string; component: LazyExoticComponent<ComponentType<PanelProps>> }>;

type PanelKey = keyof typeof PANELS;

const ICONS: Record<PanelKey, LucideIcon> = {
  myplace: Home,
  district: Landmark,
  simulation: Waves,
  janus: Telescope,
  agent: Bot,
  layers: Layers,
  research: FlaskConical,
  analytics: BarChart3,
  history: History,
  batch: FileSpreadsheet,
  alerts: Bell,
  vessels: Ship,
  insar: Radar,
};

const PRIMARY: PanelKey[] = ["myplace", "district", "simulation", "janus", "agent", "layers"];
const LAB: PanelKey[] = ["research", "analytics", "history", "batch", "alerts", "vessels", "insar"];

interface Action {
  key: string;
  label: string;
  icon: LucideIcon;
  active?: boolean;
  amber?: boolean;
  onClick: () => void;
}

function RailButton({ action, tour }: { action: Action; tour?: string }) {
  const { label, icon: Icon, active, amber, onClick } = action;
  return (
    <button
      title={label}
      aria-label={label}
      aria-pressed={active}
      data-tour={tour}
      onClick={onClick}
      className={`h-10 w-10 grid place-items-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-amber/70 ${
        active ? (amber ? "text-amber" : "text-teal") : "text-dim hover:text-ink"
      }`}
    >
      <Icon size={17} />
    </button>
  );
}

function GridButton({ action }: { action: Action }) {
  const { label, icon: Icon, active, amber, onClick } = action;
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center gap-1.5 rounded-xl ring-1 py-3 px-1.5 text-center transition-colors ${
        active
          ? amber
            ? "text-amber ring-amber/40 bg-amber/10"
            : "text-teal ring-teal/40 bg-teal/10"
          : "text-dim ring-line hover:text-ink hover:ring-teal/40"
      }`}
    >
      <Icon size={19} />
      <span className="text-[10px] leading-tight">{label}</span>
    </button>
  );
}

function Sheet({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 z-40 bg-bg/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        role="dialog"
        aria-label={title}
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 40, opacity: 0 }}
        transition={{ type: "spring", stiffness: 320, damping: 32 }}
        onClick={(e) => e.stopPropagation()}
        className="absolute inset-x-3 bottom-3 lg:inset-x-auto lg:bottom-auto lg:right-20 lg:top-1/2 lg:-translate-y-1/2 lg:w-[22rem] max-h-[70vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="font-mono text-[10px] tracking-[0.22em] text-dim uppercase">{title}</span>
          <button onClick={onClose} className="text-dim hover:text-ink transition-colors" aria-label="Close">
            <X size={16} />
          </button>
        </div>
        {children}
      </motion.div>
    </motion.div>
  );
}

export default function RightToolbar() {
  const [openPanel, setOpenPanel] = useState<PanelKey | null>(null);
  const [sheet, setSheet] = useState<"tools" | "lab" | null>(null);
  const isCompact = useIsCompact();
  const requestFlyTo = useMapStore((s) => s.requestFlyTo);
  const projection = useMapStore((s) => s.projection);
  const toggleProjection = useMapStore((s) => s.toggleProjection);
  const panelRequest = useMapStore((s) => s.panelRequest);
  const clearPanelRequest = useMapStore((s) => s.clearPanelRequest);

  useEffect(() => {
    if (!panelRequest) return;
    if (panelRequest === "close") {
      setOpenPanel(null);
      setSheet(null);
    } else if (panelRequest in PANELS) setOpenPanel(panelRequest as PanelKey);
    clearPanelRequest();
  }, [panelRequest, clearPanelRequest]);

  const zoomBy = (delta: number) => {
    const vb = useMapStore.getState().viewportBbox;
    const center: [number, number] = vb ? [(vb[0] + vb[2]) / 2, (vb[1] + vb[3]) / 2] : [25, 18];
    const span = vb ? Math.max(vb[2] - vb[0], vb[3] - vb[1]) : 90;
    const zoom = Math.log2(360 / Math.max(span, 0.01));
    requestFlyTo(center, Math.min(15, Math.max(1.5, zoom + delta)));
  };

  const panelAction = (key: PanelKey, amber = false): Action => ({
    key,
    label: PANELS[key].label,
    icon: ICONS[key],
    active: openPanel === key,
    amber,
    onClick: () => {
      setOpenPanel((current) => (current === key ? null : key));
      setSheet(null);
    },
  });

  const run = (fn: () => void) => () => {
    fn();
    setSheet(null);
  };

  const primary = PRIMARY.map((k) => panelAction(k, k === "simulation" || k === "janus"));
  const lab = LAB.map((k) => panelAction(k));
  const labOpen = LAB.includes(openPanel as PanelKey);
  const labAction: Action = {
    key: "lab",
    label: "Lab: advanced tools",
    icon: Grid3x3,
    active: labOpen || sheet === "lab",
    onClick: () => setSheet((s) => (s === "lab" ? null : "lab")),
  };
  const mapControls: Action[] = [
    {
      key: "reset-view",
      label: "Reset globe view",
      icon: Globe2,
      onClick: run(() => requestFlyTo([25, 18], 2.1)),
    },
    {
      key: "projection",
      label: projection === "globe" ? "Switch to flat map" : "Switch to 3D globe",
      icon: projection === "globe" ? MapIcon : Globe2,
      active: projection === "mercator",
      onClick: run(toggleProjection),
    },
    { key: "zoom-in", label: "Zoom in", icon: Plus, onClick: run(() => zoomBy(1)) },
    { key: "zoom-out", label: "Zoom out", icon: Minus, onClick: run(() => zoomBy(-1)) },
    {
      key: "locate",
      label: "My location",
      icon: LocateFixed,
      onClick: run(() =>
        navigator.geolocation?.getCurrentPosition((pos) =>
          requestFlyTo([pos.coords.longitude, pos.coords.latitude], 9)
        )
      ),
    },
  ];

  const Active = openPanel ? PANELS[openPanel].component : null;

  return (
    <>
      {isCompact ? (
        <button
          title="Tools"
          aria-label="Open tools"
          onClick={() => setSheet("tools")}
          className="absolute right-3 top-20 z-30 h-12 w-12 grid place-items-center rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel text-dim hover:text-ink transition-colors"
        >
          <Grid3x3 size={19} />
        </button>
      ) : (
        <nav
          aria-label="Tools"
          className="absolute right-5 top-1/2 -translate-y-1/2 z-30 flex flex-col items-center gap-2"
        >
          <div className="flex flex-col rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel divide-y divide-line overflow-hidden">
            {primary.map((a) => (
              <RailButton key={a.key} action={a} tour={`tool-${a.key}`} />
            ))}
            <RailButton action={labAction} tour="tool-lab" />
          </div>
          <div className="flex flex-col rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel divide-y divide-line overflow-hidden">
            {mapControls.map((a) => (
              <RailButton key={a.key} action={a} />
            ))}
          </div>
        </nav>
      )}

      <AnimatePresence>
        {sheet === "tools" && (
          <Sheet title="Tools" onClose={() => setSheet(null)}>
            <div className="grid grid-cols-4 gap-2.5">
              {[...primary, ...lab, ...mapControls].map((a) => (
                <GridButton key={a.key} action={a} />
              ))}
            </div>
          </Sheet>
        )}
        {sheet === "lab" && (
          <Sheet title="Lab" onClose={() => setSheet(null)}>
            <p className="text-xs text-dim mb-3 leading-relaxed">
              Research-grade tools: raw backscatter, time series, accuracy benchmarks, batch runs, alerts,
              ship screening and interferometry.
            </p>
            <div className="grid grid-cols-3 gap-2.5">
              {lab.map((a) => (
                <GridButton key={a.key} action={a} />
              ))}
            </div>
          </Sheet>
        )}
      </AnimatePresence>

      {openPanel && Active && (
        <PanelErrorBoundary
          key={openPanel}
          label={PANELS[openPanel].label}
          onDismiss={() => setOpenPanel(null)}
        >
          <Suspense fallback={null}>
            <Active onClose={() => setOpenPanel(null)} />
          </Suspense>
        </PanelErrorBoundary>
      )}
    </>
  );
}
