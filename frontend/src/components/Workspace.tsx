import { lazy, Suspense, useEffect } from "react";
import { AnimatePresence } from "framer-motion";
import Globe from "./Globe";
import TopNav from "./TopNav";
import LeftToolbar from "./LeftToolbar";
import RightToolbar from "./RightToolbar";
import ChatBar from "./Chat/ChatBar";
import Sidebar from "./Sidebar/Sidebar";
import TelemetryFooter from "./TelemetryFooter";
import MapLegend from "./Map/MapLegend";
import StatusBanner from "./StatusBanner";
import Tutorial, { TUTORIAL_SEEN_KEY } from "./Tutorial/Tutorial";
import PanelErrorBoundary from "./ErrorBoundary";
import { useMapStore } from "../stores/mapStore";
import { useSimulationStore } from "../stores/simulationStore";
import { restoreFromHash } from "../lib/share";
import { playStory, takeQueuedStory } from "../lib/featured";

const QuickAnalysisPanel = lazy(() => import("./Panels/QuickAnalysisPanel"));
const CompareSlider = lazy(() => import("./Map/CompareSlider"));
const TimelineScrubber = lazy(() => import("./Map/TimelineScrubber"));
const SimulationScrubber = lazy(() => import("./Simulation/SimulationScrubber"));
const SimulationView3D = lazy(() => import("./Simulation/SimulationView3D"));

export default function Workspace() {
  const quickAnalysisOpen = useMapStore((s) => s.quickAnalysisOpen);
  const compare = useMapStore((s) => s.compare);
  const timeline = useMapStore((s) => s.timeline);
  const setTutorialOpen = useMapStore((s) => s.setTutorialOpen);
  const flood = useSimulationStore((s) => s.sim);
  const fire = useSimulationStore((s) => s.fire);
  const view3d = useSimulationStore((s) => s.view3d);
  const setView3d = useSimulationStore((s) => s.setView3d);
  const simulation = flood ?? fire;

  useEffect(() => {
    void restoreFromHash();
    const story = takeQueuedStory();
    if (story) void playStory(story);
    let seen = false;
    try {
      seen = localStorage.getItem(TUTORIAL_SEEN_KEY) === "1";
    } catch {
      seen = false;
    }
    if (seen) return;
    const timer = setTimeout(() => setTutorialOpen(true), 1200);
    return () => clearTimeout(timer);
  }, [setTutorialOpen]);

  return (
    <div className="relative h-full w-full bg-bg overflow-hidden">
      <Globe />
      <TopNav />
      <StatusBanner />
      <Sidebar />
      <LeftToolbar />
      <RightToolbar />
      <ChatBar />
      <MapLegend />
      <TelemetryFooter />
      <PanelErrorBoundary
        label="Overlay"
        onDismiss={() => {
          useSimulationStore.getState().setView3d(false);
          useMapStore.getState().setCompare(null);
          useMapStore.getState().setTimeline(null);
        }}
      >
        <Suspense fallback={null}>
          <AnimatePresence>
            {quickAnalysisOpen && <QuickAnalysisPanel key="quick-analysis" />}
            {compare && <CompareSlider key="compare" />}
            {timeline && <TimelineScrubber key="timeline" />}
            {simulation && view3d && <SimulationView3D key="sim-3d" onClose={() => setView3d(false)} />}
            {simulation && <SimulationScrubber key="sim-scrubber" />}
          </AnimatePresence>
        </Suspense>
      </PanelErrorBoundary>
      <Tutorial />
    </div>
  );
}
