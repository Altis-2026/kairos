/** Kairos — layout composition. The globe is the page; everything floats. */
import { useEffect } from "react";
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
import MapLegend from "./components/Map/MapLegend";
import LiveWatch from "./components/Watch/LiveWatch";
import EmbedView from "./components/Embed/EmbedView";
import Tutorial, { TUTORIAL_SEEN_KEY } from "./components/Tutorial/Tutorial";
import { useMapStore } from "./stores/mapStore";
import { restoreFromHash } from "./lib/share";
import { getRoute } from "./lib/embed";

export default function App() {
  const quickAnalysisOpen = useMapStore((s) => s.quickAnalysisOpen);
  const compare = useMapStore((s) => s.compare);
  const timeline = useMapStore((s) => s.timeline);
  const setTutorialOpen = useMapStore((s) => s.setTutorialOpen);

  // Hash routes for the public/embed entry points are evaluated once at load.
  const route = getRoute();

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
  if (route === "embed") return <EmbedView />;

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
      <AnimatePresence>
        {quickAnalysisOpen && <QuickAnalysisPanel />}
        {compare && <CompareSlider />}
        {timeline && <TimelineScrubber />}
      </AnimatePresence>
      <Tutorial />
    </div>
  );
}
