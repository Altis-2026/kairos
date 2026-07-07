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
import MapLegend from "./components/Map/MapLegend";
import LiveWatch from "./components/Watch/LiveWatch";
import Guardian from "./components/Guardian/Guardian";
import EmbedView from "./components/Embed/EmbedView";
import Landing from "./components/Landing/Landing";
import Tutorial, { TUTORIAL_SEEN_KEY } from "./components/Tutorial/Tutorial";
import { useMapStore } from "./stores/mapStore";
import { restoreFromHash } from "./lib/share";
import { getRoute } from "./lib/embed";

export default function App() {
  const quickAnalysisOpen = useMapStore((s) => s.quickAnalysisOpen);
  const compare = useMapStore((s) => s.compare);
  const timeline = useMapStore((s) => s.timeline);
  const setTutorialOpen = useMapStore((s) => s.setTutorialOpen);

  const [route, setRoute] = useState(() => {
    const r = getRoute();
    if (r === "landing" && window.matchMedia("(display-mode: standalone)").matches) {
      return "app";
    }
    return r;
  });

  useEffect(() => {
    const onHashChange = () => {
      const r = getRoute();
      if (r === "landing" || r === "app") setRoute(r);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    if (route === "app") void restoreFromHash();
  }, [route]);

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
      <AnimatePresence>
        {quickAnalysisOpen && <QuickAnalysisPanel />}
        {compare && <CompareSlider />}
        {timeline && <TimelineScrubber />}
      </AnimatePresence>
      <Tutorial />
    </div>
  );
}
