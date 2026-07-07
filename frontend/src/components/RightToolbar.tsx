import {
  BarChart3,
  Bell,
  Contrast,
  FileSpreadsheet,
  FlaskConical,
  Globe2,
  History,
  Layers,
  LocateFixed,
  Map as MapIcon,
  Minus,
  Plus,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useMapStore } from "../stores/mapStore";
import LayerPanel from "./Panels/LayerPanel";
import AnalyticsPanel from "./Panels/AnalyticsPanel";
import ResearchPanel from "./Panels/ResearchPanel";
import HistoryPanel from "./Panels/HistoryPanel";
import BatchPanel from "./Panels/BatchPanel";
import AlertsPanel from "./Panels/AlertsPanel";

function ToolButton({
  title,
  active,
  onClick,
  children,
}: {
  title: string;
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      title={title}
      aria-label={title}
      onClick={onClick}
      className={`h-10 w-10 grid place-items-center transition-colors ${
        active ? "text-teal" : "text-dim hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

const CONTRAST_KEY = "kairos_high_contrast";

export default function RightToolbar() {
  const [openPanel, setOpenPanel] = useState<
    "layers" | "analytics" | "research" | "history" | "batch" | "alerts" | null
  >(null);
  const [highContrast, setHighContrast] = useState(
    () => document.documentElement.classList.contains("hc")
  );

  function toggleContrast() {
    const next = !highContrast;
    setHighContrast(next);
    document.documentElement.classList.toggle("hc", next);
    try {
      localStorage.setItem(CONTRAST_KEY, next ? "1" : "0");
    } catch {

    }
  }
  const requestFlyTo = useMapStore((s) => s.requestFlyTo);
  const projection = useMapStore((s) => s.projection);
  const toggleProjection = useMapStore((s) => s.toggleProjection);
  const panelRequest = useMapStore((s) => s.panelRequest);
  const clearPanelRequest = useMapStore((s) => s.clearPanelRequest);

  useEffect(() => {
    if (!panelRequest) return;
    const known = ["layers", "analytics", "research", "history", "batch", "alerts"];
    if (known.includes(panelRequest)) {
      setOpenPanel(panelRequest as typeof openPanel);
    }
    clearPanelRequest();
  }, [panelRequest, clearPanelRequest]);

  const zoomBy = (delta: number) => {

    const vb = useMapStore.getState().viewportBbox;
    const center: [number, number] = vb
      ? [(vb[0] + vb[2]) / 2, (vb[1] + vb[3]) / 2]
      : [25, 18];
    const span = vb ? Math.max(vb[2] - vb[0], vb[3] - vb[1]) : 90;
    const approxZoom = Math.log2(360 / Math.max(span, 0.01));
    requestFlyTo(center, Math.min(15, Math.max(1.5, approxZoom + delta)));
  };

  return (
    <>
      <div className="absolute right-2 sm:right-5 top-1/2 -translate-y-1/2 z-30 flex flex-col items-center rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel divide-y divide-line">
        <ToolButton
          title="Analytics"
          active={openPanel === "analytics"}
          onClick={() => setOpenPanel(openPanel === "analytics" ? null : "analytics")}
        >
          <BarChart3 size={17} />
        </ToolButton>
        <ToolButton
          title="Reset globe view"
          onClick={() => requestFlyTo([25, 18], 2.1)}
        >
          <Globe2 size={17} />
        </ToolButton>
        <ToolButton
          title={
            projection === "globe"
              ? "Switch to 2D flat map"
              : "Switch to 3D globe"
          }
          active={projection === "mercator"}
          onClick={toggleProjection}
        >
          {projection === "globe" ? <MapIcon size={17} /> : <Globe2 size={17} />}
        </ToolButton>
        <ToolButton
          title="Layers"
          active={openPanel === "layers"}
          onClick={() => setOpenPanel(openPanel === "layers" ? null : "layers")}
        >
          <Layers size={17} />
        </ToolButton>
        <ToolButton
          title="Research tools"
          active={openPanel === "research"}
          onClick={() => setOpenPanel(openPanel === "research" ? null : "research")}
        >
          <FlaskConical size={17} />
        </ToolButton>
        <ToolButton
          title="My analyses"
          active={openPanel === "history"}
          onClick={() => setOpenPanel(openPanel === "history" ? null : "history")}
        >
          <History size={17} />
        </ToolButton>
        <ToolButton
          title="Batch mode (CSV)"
          active={openPanel === "batch"}
          onClick={() => setOpenPanel(openPanel === "batch" ? null : "batch")}
        >
          <FileSpreadsheet size={17} />
        </ToolButton>
        <ToolButton
          title="Alerts"
          active={openPanel === "alerts"}
          onClick={() => setOpenPanel(openPanel === "alerts" ? null : "alerts")}
        >
          <Bell size={17} />
        </ToolButton>
        <ToolButton
          title="High contrast mode"
          active={highContrast}
          onClick={toggleContrast}
        >
          <Contrast size={17} />
        </ToolButton>
        <ToolButton title="Zoom in" onClick={() => zoomBy(1)}>
          <Plus size={17} />
        </ToolButton>
        <ToolButton title="Zoom out" onClick={() => zoomBy(-1)}>
          <Minus size={17} />
        </ToolButton>
        <ToolButton
          title="My location"
          onClick={() => {
            navigator.geolocation?.getCurrentPosition((pos) =>
              requestFlyTo([pos.coords.longitude, pos.coords.latitude], 9)
            );
          }}
        >
          <LocateFixed size={17} />
        </ToolButton>
      </div>

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
    </>
  );
}
