import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bell,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  FlaskConical,
  Layers,
  MessageSquare,
  MousePointerSquareDashed,
  PanelRightOpen,
  Radio,
  Satellite,
  Shield,
  Sparkles,
  X,
} from "lucide-react";
import { useMapStore } from "../../stores/mapStore";
import { useSidebarStore } from "../../stores/sidebarStore";

export const TUTORIAL_SEEN_KEY = "kairos_tutorial_seen";

interface Step {
  icon: React.ReactNode;
  chip: string;
  title: string;
  body: string;
  tip?: string;
  action?: { label: string; run: () => void };
}

function openSidebar() {
  useSidebarStore.getState().openSidebar();
}
function openPanel(name: string) {
  useMapStore.getState().requestPanel(name);
}
function openLiveWatch() {
  location.hash = "watch";
  location.reload();
}
function openGuardian() {
  location.hash = "guardian";
  location.reload();
}

const STEPS: Step[] = [
  {
    icon: <Satellite size={20} />,
    chip: "Welcome",
    title: "Real radar, plain questions",
    body:
      "Kairos runs Sentinel-1 satellite radar analysis on demand. Radar sees " +
      "through clouds and darkness, covering the whole Earth every ~12 days, " +
      "so you can ask about floods, ships, fires and more, anywhere, anytime.",
    tip: "Everything runs on free ESA satellite data. No setup needed.",
  },
  {
    icon: <MessageSquare size={20} />,
    chip: "Ask",
    title: "Just type what you want",
    body:
      "Use the bar at the bottom: “is there flooding near Dhaka right now?” " +
      "Kairos figures out the analysis type, the place and the dates, runs it, " +
      "and explains the answer in chat.",
    tip: "Try the suggestion chips above the bar for one-tap examples.",
  },
  {
    icon: <PanelRightOpen size={20} />,
    chip: "Or build it",
    title: "Prefer full control? Use the wizard",
    body:
      "Open the Menu to run the six-step builder: pick a Task, define an Area, " +
      "Configure dates, Preview scenes, Run, and read the Result. Every step is " +
      "explicit, so you always know exactly what will be analysed.",
    action: { label: "Open the wizard", run: openSidebar },
  },
  {
    icon: <MousePointerSquareDashed size={20} />,
    chip: "Area",
    title: "Draw your area of interest",
    body:
      "Use the □ box and ⊙ pin tools on the left toolbar to mark an area " +
      "on the globe. Kairos pulls Sentinel-1 coverage for exactly that footprint. " +
      "You can also search a place name up top (⌘K).",
    tip: "Smaller areas run faster and read more clearly.",
  },
  {
    icon: <Layers size={20} />,
    chip: "Analysis",
    title: "Thirteen ways to read the planet",
    body:
      "Floods and flood depth, ships, burn scars, oil spills, deforestation, " +
      "sea ice, ground change, quake damage, subsidence, urban growth, crops, " +
      "and land disturbance. Each uses a different radar signature. Kairos picks " +
      "the right one, or you choose from the task list.",
    action: { label: "Browse analysis types", run: openSidebar },
  },
  {
    icon: <Sparkles size={20} />,
    chip: "Result",
    title: "Understand what you're seeing",
    body:
      "Each result gives a headline number, a confidence score, and a coloured " +
      "overlay on the globe. The legend (bottom-left) labels every colour. Hit " +
      "“Explain this result” for a plain-language read: what it shows, the " +
      "trend, likely causes, plus an optional regional news search.",
    tip: "Radar can be fooled (e.g. wet farmland looks like flood). The explainer flags this.",
  },
  {
    icon: <FlaskConical size={20} />,
    chip: "Go deeper",
    title: "Research tools",
    body:
      "Cross-check any result: view the raw radar backscatter, overlay true-colour " +
      "optical imagery, cross-fade before/after, scrub a time-series, or estimate " +
      "the population and built-up area inside the footprint.",
    action: { label: "Open research tools", run: () => openPanel("research") },
  },
  {
    icon: <Bell size={20} />,
    chip: "Monitor",
    title: "Watch an area over time",
    body:
      "Sign in, then “Watch this area”. Kairos re-checks it on every new " +
      "Sentinel-1 pass and flags fresh detections in your Alerts panel, ideal for " +
      "monitoring a flood-prone region or a port.",
    action: { label: "Open alerts", run: () => openPanel("alerts") },
  },
  {
    icon: <FileSpreadsheet size={20} />,
    chip: "At scale",
    title: "Batch mode",
    body:
      "Have many locations? Upload a CSV of areas and analysis types to run them " +
      "all at once, watch live progress, and export the results as a single CSV.",
    action: { label: "Open batch mode", run: () => openPanel("batch") },
  },
  {
    icon: <Shield size={20} />,
    chip: "Take part",
    title: "Guardian: help patrol the planet",
    body:
      "Open Guardian, a login-free mode that spotlights real hotspots of illegal " +
      "mining, clearing and fishing. Scan a watch zone, see what the radar flags, " +
      "and submit your verdict. You help vet detections from space.",
    tip: "It's environmental transparency: candidate activity for review, never an accusation.",
    action: { label: "Open Guardian", run: openGuardian },
  },
  {
    icon: <Radio size={20} />,
    chip: "Share",
    title: "Share & Live Watch",
    body:
      "Copy a reproducible link or an embeddable widget of any result. Or open the " +
      "public Live Watch dashboard, a login-free map of active natural disasters " +
      "worldwide. You're ready to explore.",
    action: { label: "Open Live Watch", run: openLiveWatch },
  },
];

export default function Tutorial() {
  const open = useMapStore((s) => s.tutorialOpen);
  const setOpen = useMapStore((s) => s.setTutorialOpen);
  const [i, setI] = useState(0);

  const last = i === STEPS.length - 1;
  const step = STEPS[i];

  function close() {
    try {
      localStorage.setItem(TUTORIAL_SEEN_KEY, "1");
    } catch {

    }
    setOpen(false);
    setI(0);
  }

  const next = () => (last ? close() : setI((n) => n + 1));
  const prev = () => setI((n) => Math.max(0, n - 1));

  function tryIt() {
    step.action?.run();
    close();
  }

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

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 grid place-items-center bg-bg/80 backdrop-blur-sm p-5"
          onClick={close}
        >
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 260, damping: 26 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg rounded-3xl bg-surface ring-1 ring-line shadow-panel overflow-hidden"
          >

            <div className="flex items-center justify-between px-6 pt-5">
              <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.22em] text-dim">
                <Radio size={13} className="text-amber" />
                KAIROS GUIDE
              </div>
              <button
                onClick={close}
                title="Close guide (Esc)"
                className="text-dim hover:text-ink transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            <div className="px-6 pb-2 pt-4">
              <div className="flex items-center gap-3">
                <div className="h-11 w-11 grid place-items-center rounded-2xl bg-raised ring-1 ring-teal/30 text-teal">
                  {step.icon}
                </div>
                <div>
                  <div className="font-mono text-[9px] tracking-[0.2em] text-amber uppercase">
                    {i + 1} / {STEPS.length} · {step.chip}
                  </div>
                  <h2 className="font-display text-xl text-ink leading-tight mt-0.5">
                    {step.title}
                  </h2>
                </div>
              </div>

              <AnimatePresence mode="wait">
                <motion.p
                  key={i}
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -12 }}
                  transition={{ duration: 0.18 }}
                  className="mt-4 text-sm text-dim leading-relaxed"
                >
                  {step.body}
                </motion.p>
              </AnimatePresence>

              {step.tip && (
                <div className="mt-3 rounded-xl bg-bg/60 ring-1 ring-line px-3 py-2 text-[11px] text-teal/90 leading-snug">
                  {step.tip}
                </div>
              )}

              {step.action && (
                <button
                  onClick={tryIt}
                  className="mt-4 w-full h-10 rounded-xl bg-amber text-bg font-medium text-sm hover:brightness-110 transition"
                >
                  {step.action.label} →
                </button>
              )}
            </div>

            <div className="flex items-center justify-between gap-3 px-6 py-4 border-t border-line mt-2">
              <div className="flex items-center gap-1.5">
                {STEPS.map((_, idx) => (
                  <button
                    key={idx}
                    onClick={() => setI(idx)}
                    title={`Step ${idx + 1}`}
                    className={`h-1.5 rounded-full transition-all ${
                      idx === i ? "w-5 bg-teal" : "w-1.5 bg-line hover:bg-dim"
                    }`}
                  />
                ))}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={prev}
                  disabled={i === 0}
                  className="h-9 w-9 grid place-items-center rounded-xl ring-1 ring-line text-dim hover:text-ink transition disabled:opacity-30"
                  title="Back"
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  onClick={next}
                  className="h-9 px-4 rounded-xl ring-1 ring-line text-sm text-ink hover:ring-teal/50 transition flex items-center gap-1.5"
                >
                  {last ? "Done" : "Next"}
                  {!last && <ChevronRight size={15} />}
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
