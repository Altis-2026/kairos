/** Kairos — layout composition. The globe is the page; everything floats. */
import Globe from "./components/Globe";
import TopNav from "./components/TopNav";
import LeftToolbar from "./components/LeftToolbar";
import RightToolbar from "./components/RightToolbar";
import ChatBar from "./components/Chat/ChatBar";
import Sidebar from "./components/Sidebar/Sidebar";
import TelemetryFooter from "./components/TelemetryFooter";

export default function App() {
  return (
    <div className="relative h-full w-full bg-bg overflow-hidden">
      <Globe />
      <TopNav />
      <Sidebar />
      <LeftToolbar />
      <RightToolbar />
      <ChatBar />
      <TelemetryFooter />
    </div>
  );
}
