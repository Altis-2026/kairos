/** Kairos — layout composition. The globe is the page; everything floats. */
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
import { useMapStore } from "./stores/mapStore";

export default function App() {
  const quickAnalysisOpen = useMapStore((s) => s.quickAnalysisOpen);
  const compare = useMapStore((s) => s.compare);
  const timeline = useMapStore((s) => s.timeline);

  return (
    <div className="relative h-full w-full bg-bg overflow-hidden">
      <Globe />
      <TopNav />
      <Sidebar />
      <LeftToolbar />
      <RightToolbar />
      <ChatBar />
      <TelemetryFooter />
      <AnimatePresence>
        {quickAnalysisOpen && <QuickAnalysisPanel />}
        {compare && <CompareSlider />}
        {timeline && <TimelineScrubber />}
      </AnimatePresence>
    </div>
  );
}
