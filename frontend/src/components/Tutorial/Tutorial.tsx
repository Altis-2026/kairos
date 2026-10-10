import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  Flame,
  Home,
  Landmark,
  MessageSquare,
  MousePointerSquareDashed,
  Satellite,
  Telescope,
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

  target?: string;
  action?: { label: string; run: () => void };
}

function openSidebar() {
  useSidebarStore.getState().openSidebar();
}
function openPanel(name: string) {
  useMapStore.getState().requestPanel(name);
}
const STEPS: Step[] = [
  {
    icon: <Satellite size={20} />,
    chip: "Welcome",
    title: "Satellite radar, in plain language",
    body:
      "Kairos reads free radar data from Europe's Sentinel-1 satellites. Radar sees through clouds, smoke " +
      "and darkness, so you can check floods, fires, ships and land change anywhere on Earth.",
    tip: "Free, no account needed, nothing to install.",
  },
  {
    icon: <MessageSquare size={20} />,
    chip: "Ask",
    title: "Type or say your question",
    body:
      'Try "Was there flooding near Kerrville in July 2025?" Kairos works out the place, the hazard and the ' +
      "dates, runs the analysis on real radar scenes, and explains what it found.",
    tip: "Tap the microphone to ask by voice, or switch to Spanish with the ES button.",
    target: "ask",
  },
  {
    icon: <MousePointerSquareDashed size={20} />,
    chip: "Area",
    title: "Pick exactly where to look",
    body:
      "Drag a box, trace any shape, or drop a pin. The wizard behind the menu button gives you full control " +
      "over the analysis, dates and scenes.",
    target: "draw",
    action: { label: "Open the wizard", run: openSidebar },
  },
  {
    icon: <Home size={20} />,
    chip: "Prepare",
    title: "Check your own neighborhood",
    body:
      "My Place scans the area around any address for recent flooding, fire damage, new construction and " +
      "sinking ground, and explains each result in a sentence.",
    target: "tool-myplace",
    action: { label: "Open My Place", run: () => openPanel("myplace") },
  },
  {
    icon: <Landmark size={20} />,
    chip: "Lead",
    title: "A briefing for any congressional district",
    body:
      "My District loads the real boundary of any US congressional district, runs standing checks inside it, " +
      "and produces a one-page situation briefing you can print.",
    target: "tool-district",
    action: { label: "Open My District", run: () => openPanel("district") },
  },
  {
    icon: <Flame size={20} />,
    chip: "Simulate",
    title: "See what could happen next",
    body:
      "Run a flood or a wildfire over real terrain with physics models, scrub through time, and open the 3D " +
      "view to watch water fill a valley or fire climb a ridge.",
    tip: "Simulations are always labelled as simulations, never as measurements.",
    target: "tool-simulation",
    action: { label: "Open Simulate", run: () => openPanel("simulation") },
  },
  {
    icon: <Telescope size={20} />,
    chip: "Go deeper",
    title: "Janus, Agent mode and the Lab",
    body:
      "Janus is a research mentor that runs real analyses with you. Agent mode turns a goal into a plan of " +
      "analyses and a report. The Lab holds the research tools: accuracy benchmarks, time series, InSAR, dark " +
      "vessels and batch runs.",
    target: "tool-janus",
    action: { label: "Open Janus", run: () => openPanel("janus") },
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
  const cardRef = useRef<HTMLDivElement>(null);

  const last = i === STEPS.length - 1;
  const step = STEPS[i];

  function close() {
    try {
      localStorage.setItem(TUTORIAL_SEEN_KEY, "1");
    } catch {}
    setOpen(false);
    setI(0);
  }

  const next = () => (last ? close() : setI((n) => n + 1));
  const prev = () => setI((n) => Math.max(0, n - 1));

  function tryIt() {
    step.action?.run();
    close();
  }

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

    if (!rect) {
      setPos({ left: (vw - cw) / 2, top: (vh - ch) / 2 });
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
    else setPos({ left: (vw - cw) / 2, top: (vh - ch) / 2 });
  }, [rect, open, i]);

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
    ? {
        x: rect.left - pad,
        y: rect.top - pad,
        width: rect.width + pad * 2,
        height: rect.height + pad * 2,
      }
    : null;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="tour"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50"
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
              fill="rgba(11,18,14,0.82)"
              mask="url(#kairos-tour-mask)"
            />
          </svg>

          {hole ? (
            <>
              <div
                className="absolute left-0 right-0 top-0"
                style={{ height: Math.max(hole.y, 0) }}
                onClick={close}
              />
              <div
                className="absolute left-0 right-0 bottom-0"
                style={{ top: hole.y + hole.height }}
                onClick={close}
              />
              <div
                className="absolute left-0"
                style={{ top: hole.y, height: hole.height, width: Math.max(hole.x, 0) }}
                onClick={close}
              />
              <div
                className="absolute right-0"
                style={{ top: hole.y, height: hole.height, left: hole.x + hole.width }}
                onClick={close}
              />
            </>
          ) : (
            <div className="absolute inset-0" onClick={close} />
          )}

          {hole && (
            <motion.div
              layout
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="pointer-events-none absolute rounded-[14px] ring-2 ring-amber shadow-[0_0_0_6px_rgba(232,163,24,0.18)]"
              style={{
                left: hole.x,
                top: hole.y,
                width: hole.width,
                height: hole.height,
              }}
            />
          )}

          <motion.div
            ref={cardRef}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "spring", stiffness: 260, damping: 26 }}
            onClick={(e) => e.stopPropagation()}
            className="absolute w-[min(24rem,calc(100vw-2rem))] max-h-[85vh] overflow-y-auto rounded-3xl bg-surface ring-1 ring-line shadow-panel"
            style={{
              left: pos?.left ?? 0,
              top: pos?.top ?? 0,

              visibility: pos ? "visible" : "hidden",
            }}
          >
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
                <motion.p
                  key={i}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.16 }}
                  className="mt-3 text-[13px] text-dim leading-relaxed"
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
                  className="mt-3 w-full h-10 rounded-xl bg-amber text-bg font-medium text-sm hover:brightness-110 transition"
                >
                  {step.action.label} →
                </button>
              )}
            </div>

            <div className="flex items-center justify-between gap-3 px-5 py-3.5 border-t border-line mt-2">
              <div className="flex items-center gap-1.5 flex-wrap">
                {STEPS.map((_, idx) => (
                  <button
                    key={idx}
                    onClick={() => setI(idx)}
                    aria-label={`Step ${idx + 1}`}
                    title={`Step ${idx + 1}`}
                    className={`h-1.5 rounded-full transition-all ${
                      idx === i ? "w-5 bg-teal" : "w-1.5 bg-line hover:bg-dim"
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
