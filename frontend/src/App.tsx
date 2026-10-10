import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { MotionConfig } from "framer-motion";
import { AppErrorBoundary } from "./components/ErrorBoundary";
import { getRoute, type Route } from "./lib/embed";
import { onRouteChange } from "./lib/navigation";
import { usePrefsStore } from "./stores/prefsStore";

const Workspace = lazy(() => import("./components/Workspace"));
const Landing = lazy(() => import("./components/Landing/Landing"));
const LiveWatch = lazy(() => import("./components/Watch/LiveWatch"));
const Guardian = lazy(() => import("./components/Guardian/Guardian"));
const Foresight = lazy(() => import("./components/Foresight/Foresight"));
const EmbedView = lazy(() => import("./components/Embed/EmbedView"));
const Academy = lazy(() => import("./components/Academy/Academy"));
const About = lazy(() => import("./components/About/About"));

function initialRoute(): Route {
  const r = getRoute();
  if (r === "landing" && window.matchMedia("(display-mode: standalone)").matches) return "app";
  return r;
}

function Loading() {
  return (
    <div className="h-full w-full grid place-items-center bg-bg" role="status" aria-label="Loading Kairos">
      <div className="h-10 w-10 rounded-full border-2 border-line border-t-teal animate-spin" />
    </div>
  );
}

export default function App() {
  const [route, setRoute] = useState<Route>(initialRoute);
  const previous = useRef<Route>(route);
  const locale = usePrefsStore((s) => s.locale);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  useEffect(() => {
    const onHashChange = () => {
      const next = getRoute();
      if (next === previous.current) return;
      onRouteChange(previous.current, next);
      previous.current = next;
      setRoute(next);
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const view = {
    app: <Workspace />,
    landing: <Landing onLaunch={() => (location.hash = "app")} />,
    watch: <LiveWatch />,
    guardian: <Guardian />,
    foresight: <Foresight />,
    embed: <EmbedView />,
    academy: <Academy />,
    about: <About />,
  }[route];

  return (
    <AppErrorBoundary>
      <MotionConfig reducedMotion="user">
        <Suspense fallback={<Loading />}>{view}</Suspense>
      </MotionConfig>
    </AppErrorBoundary>
  );
}
