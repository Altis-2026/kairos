/** Kairos — layout composition. The globe is the page; everything floats. */
import { useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";
import Globe from "./components/Globe";
import TopNav from "./components/TopNav";
import LeftToolbar from "./components/LeftToolbar";
import RightToolbar from "./components/RightToolbar";
import ChatBar from "./components/Chat/ChatBar";
import Sidebar from "./components/Sidebar/Sidebar";
import TelemetryFooter from "./components/TelemetryFooter";
import QuickAnalysisPanel from "./components/Panels/QuickAnalysisPanel";
import CompareSlider from "./components/Map/CompareSlider";
import TimelineScrubber from "./components/Map/TimelineScrubber";
import SimulationScrubber from "./components/Simulation/SimulationScrubber";
import SimulationView3D from "./components/Simulation/SimulationView3D";
import MapLegend from "./components/Map/MapLegend";
import LiveWatch from "./components/Watch/LiveWatch";
import Guardian from "./components/Guardian/Guardian";
import Foresight from "./components/Foresight/Foresight";
import EmbedView from "./components/Embed/EmbedView";
import Landing from "./components/Landing/Landing";
import Tutorial, { TUTORIAL_SEEN_KEY } from "./components/Tutorial/Tutorial";
import { useMapStore } from "./stores/mapStore";
import { useSimulationStore } from "./stores/simulationStore";
import { restoreFromHash } from "./lib/share";
import { getRoute } from "./lib/embed";

export default function App() {
  const quickAnalysisOpen = useMapStore((s) => s.quickAnalysisOpen);
  const compare = useMapStore((s) => s.compare);
  const timeline = useMapStore((s) => s.timeline);
  // Either forward model. Both mount the same scrubber and the same 3D view,
  // which branch internally on which one is loaded.
  const flood = useSimulationStore((s) => s.sim);
  const fire = useSimulationStore((s) => s.fire);
  const simulation = flood ?? fire;
  const view3d = useSimulationStore((s) => s.view3d);
  const setView3d = useSimulationStore((s) => s.setView3d);
  const setTutorialOpen = useMapStore((s) => s.setTutorialOpen);

  // A bare URL shows the landing page; installed-PWA launches skip it.
  const [route, setRoute] = useState(() => {
    const r = getRoute();
    if (r === "landing" && window.matchMedia("(display-mode: standalone)").matches) {
      return "app";
    }
    return r;
  });

  // Every route responds to the hash, so browser back/forward moves between
  // the public views the same way the nav buttons do. (Those buttons also
  // reload, which remounts the globe cleanly; this keeps the plain
  // edit-the-URL and back-button paths working too.)
  useEffect(() => {
    const onHashChange = () => setRoute(getRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  // A shared link (#task=...&bbox=...) re-runs its analysis onto the globe.
  useEffect(() => {
    if (route === "app") void restoreFromHash();
  }, [route]);

  // First-time visitors get the guide once; afterwards it's the ? button.
  useEffect(() => {
    if (route !== "app") return;
    let seen = false;
    try {
      seen = localStorage.getItem(TUTORIAL_SEEN_KEY) === "1";
    } catch {
      seen = false;
    }
    if (!seen) setTutorialOpen(true);
  }, [route, setTutorialOpen]);

  if (route === "watch") return <LiveWatch />;
  if (route === "guardian") return <Guardian />;
  if (route === "foresight") return <Foresight />;
  if (route === "embed") return <EmbedView />;
  if (route === "landing") {
    return (
      <Landing
        onLaunch={() => {
          location.hash = "app";
          setRoute("app");
        }}
      />
    );
  }

  return (
    <div className="relative h-full w-full bg-bg overflow-hidden">
      <Globe />
      <TopNav />
      <Sidebar />
      <LeftToolbar />
      <RightToolbar />
      <ChatBar />
      <MapLegend />
      <TelemetryFooter />
      {/* AnimatePresence tracks children by key; without explicit ones it
          falls back to positional keys and collides as these toggle. */}
      <AnimatePresence>
        {quickAnalysisOpen && <QuickAnalysisPanel key="quick-analysis" />}
        {compare && <CompareSlider key="compare" />}
        {timeline && <TimelineScrubber key="timeline" />}
        {simulation && view3d && (
          <SimulationView3D key="sim-3d" onClose={() => setView3d(false)} />
        )}
        {simulation && <SimulationScrubber key="sim-scrubber" />}
      </AnimatePresence>
      <Tutorial />
    </div>
  );
}
