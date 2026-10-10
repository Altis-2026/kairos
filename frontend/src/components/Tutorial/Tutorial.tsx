import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  BarChart3,
  Bot,
  Check,
  ChevronLeft,
  ChevronRight,
  Compass,
  Flame,
  GraduationCap,
  Home,
  Landmark,
  Languages,
  Layers,
  MessageSquare,
  MousePointerClick,
  PanelLeftOpen,
  Radio,
  Satellite,
  Share2,
  Sparkles,
  Telescope,
  Waves,
  X,
} from "lucide-react";
import { useMapStore } from "../../stores/mapStore";
import { useSidebarStore } from "../../stores/sidebarStore";
import { useChatStore } from "../../stores/chatStore";
import { usePrefsStore } from "../../stores/prefsStore";
import { useSimulationStore } from "../../stores/simulationStore";

export const TUTORIAL_SEEN_KEY = "kairos_tutorial_seen";

interface Task {
  text: string;
  done: () => boolean;
}

interface Step {
  icon: ReactNode;
  chip: string;
  title: string;
  body: string[];
  points?: string[];
  tip?: string;
  target?: string;
  side?: "start";
  task?: Task;
  action?: { label: string; run: () => void };
}

const openSidebar = () => useSidebarStore.getState().openSidebar();
const openPanel = (name: string) => useMapStore.getState().requestPanel(name);
const panelOpen = (tour: string) => () =>
  document.querySelector(`[data-tour="${tour}"]`)?.getAttribute("aria-pressed") === "true";

const STEPS: Step[] = [
  {
    icon: <Satellite size={20} />,
    chip: "Welcome",
    title: "Satellite radar, in plain language",
    body: [
      "Kairos reads free radar data from Europe's Sentinel-1 satellites. Radar sends its own microwave pulse and times the echo, so it sees through clouds, smoke and darkness that blind ordinary camera satellites.",
      "This tour takes about three minutes. Most steps have a small task you can try for real, and you can leave at any time with Esc.",
    ],
    points: [
      "Ask questions in English or Spanish, typed or spoken",
      "Measure floods, fires, ships, deforestation and more",
      "Simulate what could happen next, then plan for it",
    ],
    tip: "Everything runs on free, public satellite data.",
  },
  {
    icon: <MessageSquare size={20} />,
    chip: "Ask",
    title: "Just type your question",
    body: [
      "The bar at the bottom is the fastest way in. Describe what you want to know and where, and Kairos works out the analysis, the place and the dates, runs it on real radar scenes, and explains what it found.",
      'Try "Was there flooding near Kerrville in July 2025?" or tap one of the example chips above the bar.',
    ],
    points: [
      'Follow-ups remember context: "what about last year?"',
      "One question can run several analyses at once",
      "Tap Stop any time to cancel",
    ],
    target: "ask",
    task: {
      text: "Send any question or tap an example chip",
      done: () => useChatStore.getState().messages.length > 0,
    },
  },
  {
    icon: <Languages size={20} />,
    chip: "Voice and language",
    title: "Speak it, or switch to Spanish",
    body: [
      "Tap the microphone in the question bar to ask out loud, and turn on the speaker icon to hear answers read back. Kairos answers in whatever language you ask in.",
      "The ES button switches the whole interface to Spanish, including the chat suggestions and the voice settings.",
    ],
    target: "language",
    task: {
      text: "Switch the language, then switch back",
      done: () => usePrefsStore.getState().locale === "es",
    },
  },
  {
    icon: <Compass size={20} />,
    chip: "Stories",
    title: "Start with a real disaster",
    body: [
      "Featured stories load real events straight onto the globe: the 2025 Texas Hill Country floods, the 2022 Pakistan monsoon, the Lahaina wildfire, the Turkey earthquake, Amazon clearing and the Hunga Tonga eruption.",
      "They are pre-computed in the background, so they open in seconds. It is the best way to see what a result looks like.",
    ],
    target: "stories",
    task: {
      text: "Open the book icon and pick a story",
      done: () => useMapStore.getState().layers.length > 0,
    },
  },
  {
    icon: <MousePointerClick size={20} />,
    chip: "Area",
    title: "Choose exactly where to look",
    body: [
      "These tools set the area for an analysis. Drag a rectangle, trace any shape point by point, drop a pin that makes a 50 km box, or use the lightning bolt to drop a pin and run an analysis instantly.",
      "The small number under the tools is the area in square kilometers. Smaller areas run faster and read more clearly.",
    ],
    points: [
      "Click to add points, then double-click or press Enter to close a shape",
      "Esc cancels a drawing",
    ],
    target: "draw",
    task: { text: "Draw a box or shape on the globe", done: () => useMapStore.getState().aoi !== null },
  },
  {
    icon: <PanelLeftOpen size={20} />,
    chip: "Wizard",
    title: "Full control with the wizard",
    body: [
      "The Menu button opens a guided six-step builder: choose a task, define the area, set the dates, preview which radar passes exist, run, and read the result.",
      "It is the same engine as the chat, with every choice made explicit. Handy when you want a specific date window or want to check that a satellite actually passed over.",
    ],
    target: "menu",
    task: { text: "Open the wizard", done: () => useSidebarStore.getState().open },
    action: { label: "Open the wizard", run: openSidebar },
  },
  {
    icon: <Sparkles size={20} />,
    chip: "Results",
    title: "Reading a result",
    body: [
      "Every result shows a colored overlay on the globe, a headline number, a confidence score, the date of the satellite pass, and a plain-language explanation.",
      "Radar can be fooled. Wet farmland can look like flooding and calm water can look like an oil slick, so Kairos says so rather than hiding it.",
    ],
    points: [
      "Explain this result: what it shows, the trend and likely causes",
      "Test other explanations: checks real rainfall, wind and land cover",
      "Compare, time series and optical views live in the Lab",
      "Share a link, embed it, or export a GeoTIFF and report",
    ],
    tip: "Confidence reflects data availability and method reliability, not a guarantee.",
  },
  {
    icon: <Home size={20} />,
    chip: "Prepare",
    title: "Check your own neighborhood",
    body: [
      "My Place scans around any address for recent flooding, fire damage, new construction and sinking ground, and explains each result in one sentence a neighbor could read.",
      "From there you can open Foresight for decades of hazard history and a preparedness checklist.",
    ],
    target: "tool-myplace",
    side: "start",
    task: { text: "Open My Place", done: panelOpen("tool-myplace") },
    action: { label: "Open My Place", run: () => openPanel("myplace") },
  },
  {
    icon: <Landmark size={20} />,
    chip: "Lead",
    title: "A briefing for any congressional district",
    body: [
      "My District loads the real boundary of any US congressional district from the Census Bureau, then runs six standing checks inside it: flooding, burn scars, drought, crop health, new construction and sinking ground.",
      "It can also simulate a flood or wildfire nearby and turns the findings into a one-page situation briefing you can print or save as a PDF.",
    ],
    points: ["Type a state and number, like TX and 26", "Run all checks with one click"],
    target: "tool-district",
    side: "start",
    task: { text: "Open My District", done: panelOpen("tool-district") },
    action: { label: "Open My District", run: () => openPanel("district") },
  },
  {
    icon: <Waves size={20} />,
    chip: "Simulate",
    title: "See what could happen next",
    body: [
      "Simulate runs physics models on real terrain. Flooding uses a shallow-water solver, and wildfire uses the Rothermel spread equations with fuel, wind and slope.",
      "Pick a showcase scene, scrub through time, and open the 3D view to watch water fill a valley or fire climb a ridge.",
    ],
    tip: "Simulations are always labelled as simulations. They model something that has not happened, never a measurement.",
    target: "tool-simulation",
    side: "start",
    task: { text: "Open Simulate", done: panelOpen("tool-simulation") },
    action: { label: "Open Simulate", run: () => openPanel("simulation") },
  },
  {
    icon: <Flame size={20} />,
    chip: "Simulate",
    title: "Scrub, play and fly",
    body: [
      "Once a simulation is loaded, a scrubber appears along the bottom. Drag it or press play to move through time, change the speed, and watch the numbers update.",
      "The 3D view turns the globe into a terrain model you can orbit, with a shimmering water surface and a basemap draped over the ground.",
    ],
    points: ["Drag to orbit, scroll to zoom", "Depth scale and opacity sliders change how it reads"],
    task: {
      text: "Load a scene from the Simulate panel",
      done: () => useSimulationStore.getState().sim !== null || useSimulationStore.getState().fire !== null,
    },
  },
  {
    icon: <Telescope size={20} />,
    chip: "Learn",
    title: "Janus, your research mentor",
    body: [
      "Janus teaches you how a scientist would answer a question, then works alongside you. It runs real analyses during the conversation, searches the literature, checks results against ground truth and pushes back on weak reasoning.",
      "Projects are remembered, and you can export to LaTeX, BibTeX, a runnable notebook or a policy brief. It is free for everyone.",
    ],
    target: "tool-janus",
    side: "start",
    task: { text: "Open Janus", done: panelOpen("tool-janus") },
    action: { label: "Open Janus", run: () => openPanel("janus") },
  },
  {
    icon: <Bot size={20} />,
    chip: "Learn",
    title: "Agent mode",
    body: [
      'Give Agent mode a goal instead of a question, like "find the newest deforestation across the Amazon this month." It plans up to four analyses, runs them with live progress, and writes a report across all of them.',
    ],
    target: "tool-agent",
    side: "start",
    task: { text: "Open Agent mode", done: panelOpen("tool-agent") },
    action: { label: "Open Agent mode", run: () => openPanel("agent") },
  },
  {
    icon: <Layers size={20} />,
    chip: "Layers",
    title: "Layers and the Lab",
    body: [
      "Layers lists everything drawn on the globe, with opacity sliders, visibility toggles and a switch for past disasters from NASA.",
      "The Lab drawer holds the research tools: raw backscatter, optical comparison, before and after swipe, time series with trend tests, measured accuracy against independent reference maps, batch CSV runs, area alerts, dark-vessel screening and InSAR interferograms.",
    ],
    target: "tool-layers",
    side: "start",
    task: { text: "Open Layers", done: panelOpen("tool-layers") },
    action: { label: "Open Layers", run: () => openPanel("layers") },
  },
  {
    icon: <BarChart3 size={20} />,
    chip: "Lab",
    title: "Measured accuracy",
    body: [
      "Open the Lab and choose Research tools to find the accuracy benchmarks. They re-run Kairos's detectors over historical disasters and score them live against independent reference maps, reporting intersection over union, precision, recall and F1.",
      "Nothing is precomputed, so the numbers are honest.",
    ],
    target: "tool-lab",
    side: "start",
    task: { text: "Open the Lab", done: panelOpen("tool-lab") },
  },
  {
    icon: <Radio size={20} />,
    chip: "Watch",
    title: "Live Watch and Foresight",
    body: [
      "Live Watch is a public map of active disasters worldwide from NASA, one click away from a radar analysis of any of them. Kairos also checks these events by itself every few hours and posts what it finds.",
      "Foresight turns decades of satellite record into flood, wildfire, drought and subsidence scores for any place, with seasonal peaks and statistical trend tests.",
    ],
    target: "nav-watch",
  },
  {
    icon: <GraduationCap size={20} />,
    chip: "Learn",
    title: "Academy and Guardian",
    body: [
      "The Academy has five short lessons on how radar sees the Earth, three narrated real cases you can rerun yourself, and a quiz. It is the fastest way to learn to read the images.",
      "Guardian is a citizen-science mode that spotlights possible illegal mining and clearing in protected areas for you to review.",
    ],
    target: "nav-academy",
  },
  {
    icon: <Share2 size={20} />,
    chip: "Share",
    title: "Share, export and install",
    body: [
      "Any result becomes a link that reruns the same analysis for whoever opens it, or an embeddable widget for a website. Exports include a GeoTIFF, a methodology report and a printable briefing.",
      "Kairos installs like an app from your browser's menu, and signing in with Google adds saved analyses and alerts. Everything else works without an account.",
    ],
  },
  {
    icon: <Check size={20} />,
    chip: "Done",
    title: "You are ready",
    body: [
      "That is the whole tour. A good first move is a featured story, then try your own address in My Place.",
      "You can replay this guide any time with the question mark button at the top right.",
    ],
    tip: "Built by Amogh Vinaykumar and Prem Kamasani. Questions or ideas are welcome on GitHub.",
  },
];

const GAP = 18;
const MARGIN = 16;

function clamp(v: number, lo: number, hi: number) {
  return Math.min(Math.max(v, lo), hi);
}

export default function Tutorial() {
  const open = useMapStore((s) => s.tutorialOpen);
  const setOpen = useMapStore((s) => s.setTutorialOpen);
  const [i, setI] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  const [done, setDone] = useState(false);
  const [everDone, setEverDone] = useState<Set<number>>(() => new Set());
  const cardRef = useRef<HTMLDivElement>(null);
  const latched = useRef<Set<number>>(new Set());

  const last = i === STEPS.length - 1;
  const step = STEPS[i];

  function close() {
    try {
      localStorage.setItem(TUTORIAL_SEEN_KEY, "1");
    } catch {}
    openPanel("close");
    useSidebarStore.getState().closeSidebar();
    setOpen(false);
    setI(0);
    setEverDone(new Set());
    latched.current = new Set();
  }

  const next = () => (last ? close() : setI((n) => n + 1));
  const prev = () => setI((n) => Math.max(0, n - 1));

  useEffect(() => {
    if (!open) return;
    const check = () => {
      const value = step.task ? step.task.done() : false;
      if (value && !latched.current.has(i)) {
        latched.current.add(i);
        setEverDone(new Set(latched.current));
      }
      setDone(value || latched.current.has(i));
    };
    check();
    if (!step.task) return;
    const timer = window.setInterval(check, 350);
    return () => window.clearInterval(timer);
  }, [open, i, step]);

  useLayoutEffect(() => {
    if (!open) return;
    const measure = () => {
      const el = step.target ? document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`) : null;
      setRect(el ? el.getBoundingClientRect() : null);
    };
    measure();
    const settle = window.setTimeout(measure, 320);
    window.addEventListener("resize", measure);
    return () => {
      window.clearTimeout(settle);
      window.removeEventListener("resize", measure);
    };
  }, [open, i, step.target]);

  useLayoutEffect(() => {
    const card = cardRef.current;
    if (!open || !card) return;
    const cw = card.offsetWidth;
    const ch = card.offsetHeight;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const center = { left: (vw - cw) / 2, top: (vh - ch) / 2 };

    if (!rect) {
      setPos(center);
      return;
    }
    if (step.side === "start" && vw >= 1100) {
      setPos({ left: 92, top: clamp(rect.top + rect.height / 2 - ch / 2, MARGIN, vh - ch - MARGIN) });
      return;
    }

    const fitsLeft = rect.left - GAP - MARGIN >= cw;
    const fitsRight = vw - rect.right - GAP - MARGIN >= cw;
    const fitsAbove = rect.top - GAP - MARGIN >= ch;
    const fitsBelow = vh - rect.bottom - GAP - MARGIN >= ch;
    const midY = clamp(rect.top + rect.height / 2 - ch / 2, MARGIN, vh - ch - MARGIN);
    const midX = clamp(rect.left + rect.width / 2 - cw / 2, MARGIN, vw - cw - MARGIN);

    if (fitsLeft) setPos({ left: rect.left - GAP - cw, top: midY });
    else if (fitsRight) setPos({ left: rect.right + GAP, top: midY });
    else if (fitsAbove) setPos({ left: midX, top: rect.top - GAP - ch });
    else if (fitsBelow) setPos({ left: midX, top: rect.bottom + GAP });
    else setPos(center);
  }, [rect, open, i, step.side]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, i]);

  const pad = 6;
  const hole = rect
    ? { x: rect.left - pad, y: rect.top - pad, width: rect.width + pad * 2, height: rect.height + pad * 2 }
    : null;
  const progress = ((i + 1) / STEPS.length) * 100;

  if (!open) return null;

  return (
    <motion.div
      key="tour"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="pointer-events-none fixed inset-0 z-50"
      role="dialog"
      aria-label="Kairos guided tour"
    >
      <svg className="pointer-events-none absolute inset-0 h-full w-full">
        <defs>
          <mask id="kairos-tour-mask">
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            {hole && (
              <rect x={hole.x} y={hole.y} width={hole.width} height={hole.height} rx="14" fill="black" />
            )}
          </mask>
        </defs>
        <rect
          x="0"
          y="0"
          width="100%"
          height="100%"
          fill="rgba(11,18,14,0.66)"
          mask="url(#kairos-tour-mask)"
        />
      </svg>

      {hole ? (
        <>
          <div
            className="absolute left-0 right-0 top-0 pointer-events-auto"
            style={{ height: Math.max(hole.y, 0) }}
            onClick={close}
          />
          <div
            className="absolute left-0 right-0 bottom-0 pointer-events-auto"
            style={{ top: hole.y + hole.height }}
            onClick={close}
          />
          <div
            className="absolute left-0 pointer-events-auto"
            style={{ top: hole.y, height: hole.height, width: Math.max(hole.x, 0) }}
            onClick={close}
          />
          <div
            className="absolute right-0 pointer-events-auto"
            style={{ top: hole.y, height: hole.height, left: hole.x + hole.width }}
            onClick={close}
          />
        </>
      ) : (
        <div className="absolute inset-0 pointer-events-auto" onClick={close} />
      )}

      {hole && (
        <motion.div
          layout
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="pointer-events-none absolute rounded-[14px] ring-2 ring-amber shadow-[0_0_0_6px_rgba(232,163,24,0.18)] animate-pulse-soft"
          style={{ left: hole.x, top: hole.y, width: hole.width, height: hole.height }}
        />
      )}

      <motion.div
        ref={cardRef}
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 260, damping: 26 }}
        onClick={(e) => e.stopPropagation()}
        className="pointer-events-auto absolute w-[min(26rem,calc(100vw-2rem))] max-h-[88vh] overflow-y-auto rounded-3xl bg-surface ring-1 ring-line shadow-panel"
        style={{ left: pos?.left ?? 0, top: pos?.top ?? 0, visibility: pos ? "visible" : "hidden" }}
      >
        <div className="h-1 w-full bg-line/60 rounded-t-3xl overflow-hidden">
          <motion.div
            className="h-full bg-teal"
            animate={{ width: `${progress}%` }}
            transition={{ type: "spring", stiffness: 200, damping: 28 }}
          />
        </div>

        <div className="flex items-center justify-between px-5 pt-4">
          <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.22em] text-dim">
            <Satellite size={13} className="text-amber" />
            KAIROS GUIDE
          </div>
          <button
            onClick={close}
            title="Close guide (Esc)"
            aria-label="Close guide"
            className="text-dim hover:text-ink transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="px-5 pb-2 pt-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 shrink-0 grid place-items-center rounded-2xl bg-raised ring-1 ring-teal/30 text-teal">
              {step.icon}
            </div>
            <div className="min-w-0">
              <div className="font-mono text-[9px] tracking-[0.2em] text-amber uppercase">
                {i + 1} / {STEPS.length} · {step.chip}
              </div>
              <h2 className="font-display text-lg text-ink leading-tight mt-0.5">{step.title}</h2>
            </div>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={i}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.16 }}
              className="mt-3 space-y-2.5"
            >
              {step.body.map((paragraph) => (
                <p key={paragraph} className="text-[13px] text-dim leading-relaxed">
                  {paragraph}
                </p>
              ))}
              {step.points && (
                <ul className="space-y-1">
                  {step.points.map((point) => (
                    <li key={point} className="flex gap-2 text-[12px] text-ink/85 leading-snug">
                      <span className="text-teal shrink-0">·</span>
                      {point}
                    </li>
                  ))}
                </ul>
              )}
            </motion.div>
          </AnimatePresence>

          {step.tip && (
            <div className="mt-3 rounded-xl bg-bg/60 ring-1 ring-line px-3 py-2 text-[11px] text-teal/90 leading-snug">
              {step.tip}
            </div>
          )}

          {step.task && (
            <div
              className={`mt-3 flex items-center gap-2.5 rounded-xl px-3 py-2.5 ring-1 transition-colors ${
                done ? "bg-teal/10 ring-teal/50" : "bg-bg/60 ring-amber/40"
              }`}
              aria-live="polite"
            >
              <span
                className={`h-5 w-5 shrink-0 grid place-items-center rounded-full ring-1 transition-colors ${
                  done ? "bg-teal text-bg ring-teal" : "ring-amber/60 text-transparent"
                }`}
              >
                <Check size={12} />
              </span>
              <span className="min-w-0 text-[12px] text-ink leading-snug">
                <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-amber mr-1.5">
                  {done ? "Done" : "Your turn"}
                </span>
                {step.task.text}
              </span>
            </div>
          )}

          {step.action && !done && (
            <button
              onClick={() => step.action?.run()}
              className="mt-3 w-full h-10 rounded-xl bg-amber text-bg font-medium text-sm hover:brightness-110 transition"
            >
              {step.action.label}
            </button>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 px-5 py-3.5 border-t border-line mt-2">
          <div className="flex items-center gap-1 flex-wrap max-w-[14rem]">
            {STEPS.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setI(idx)}
                aria-label={`Step ${idx + 1}`}
                title={`Step ${idx + 1}`}
                className={`h-1.5 rounded-full transition-all ${
                  idx === i
                    ? "w-4 bg-teal"
                    : everDone.has(idx)
                      ? "w-1.5 bg-teal/60"
                      : "w-1.5 bg-line hover:bg-dim"
                }`}
              />
            ))}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={prev}
              disabled={i === 0}
              className="h-9 w-9 grid place-items-center rounded-xl ring-1 ring-line text-dim hover:text-ink transition disabled:opacity-30"
              aria-label="Back"
              title="Back"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={next}
              className={`h-9 px-4 rounded-xl text-sm flex items-center gap-1.5 transition ${
                done || last
                  ? "bg-teal text-bg font-medium hover:brightness-110"
                  : "ring-1 ring-line text-ink hover:ring-teal/50"
              }`}
            >
              {last ? "Finish" : "Next"}
              {!last && <ChevronRight size={15} />}
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
