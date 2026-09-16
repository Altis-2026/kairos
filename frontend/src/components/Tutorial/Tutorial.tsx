/**
 * Kairos Guide: a spotlight walkthrough of the live UI (the ? button).
 *
 * Each step points at the actual control it describes. The rest of the screen
 * dims through an SVG mask with a hole cut over the target, a ring marks it,
 * and the card places itself on whichever side has room — so the thing being
 * explained is never the thing hidden behind the explanation.
 *
 * Targets are `data-tour` hooks rather than CSS classes or visible labels.
 * Both of those change for cosmetic reasons and would break the tour silently;
 * a named hook is a deliberate contract.
 *
 * Any step whose target is missing degrades to a centred card with no
 * spotlight. That is the normal case on a narrow screen, where the right-hand
 * tool rail collapses into a single sheet launcher and most targets genuinely
 * do not exist.
 *
 * Opens on first visit (remembered in localStorage) and from the ? in the nav.
 */
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bell,
  ChevronLeft,
  ChevronRight,
  Flame,
  FlaskConical,
  Layers,
  MessageSquare,
  MousePointerSquareDashed,
  PanelRightOpen,
  Radar,
  Radio,
  Satellite,
  Ship,
  Sparkles,
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
  /** `data-tour` value of the control this step is about. */
  target?: string;
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
      "through cloud and darkness and covers the whole Earth every ~12 days, " +
      "so you can ask about floods, ships, fires and more — anywhere, any time.",
    tip: "Everything here runs on free ESA satellite data. Nothing to install.",
  },
  {
    icon: <MessageSquare size={20} />,
    chip: "Ask",
    title: "Just type what you want",
    body:
      "“Is there flooding near Dhaka right now?” Kairos works out the analysis " +
      "type, the place and the dates, runs it, and explains the answer back to " +
      "you in chat.",
    tip: "The chips just above the bar are one-tap examples to start from.",
    target: "ask",
  },
  {
    icon: <MousePointerSquareDashed size={20} />,
    chip: "Area",
    title: "Draw where you want to look",
    body:
      "Use this box tool to drag an area on the globe, or the pin below it to " +
      "drop a ~50 km box. Kairos pulls Sentinel-1 coverage for exactly that " +
      "footprint. You can also search a place by name up top (⌘K).",
    tip: "Smaller areas run faster and read more clearly.",
    target: "draw",
  },
  {
    icon: <PanelRightOpen size={20} />,
    chip: "Or build it",
    title: "Want full control? Use the wizard",
    body:
      "The Menu opens a six-step builder: pick a Task, define an Area, " +
      "Configure dates, Preview the scenes, Run, and read the Result. Every " +
      "step is explicit, so you always know exactly what is being analysed.",
    target: "menu",
    action: { label: "Open the wizard", run: openSidebar },
  },
  {
    icon: <Layers size={20} />,
    chip: "Analyses",
    title: "22 ways to read the planet",
    body:
      "Floods (even under forest canopy), ships, burn scars, oil spills, " +
      "deforestation, sea ice and drift, subsidence, urban growth, crops, " +
      "biomass, methane, air quality, snow melt — even L-band archaeology. " +
      "Flood Consensus runs radar and optical independently and maps where the " +
      "two agree.",
    target: "tool-layers",
    action: { label: "Browse analysis types", run: openSidebar },
  },
  {
    icon: <Sparkles size={20} />,
    chip: "Results",
    title: "Understand what you're seeing",
    body:
      "Every result carries a headline number, a confidence score and a " +
      "coloured overlay, with a legend that labels each colour. “Explain this " +
      "result” gives a plain-language read: what it shows, the trend, likely " +
      "causes, and an optional regional news search.",
    tip: "Radar can be fooled — wet farmland can look like flood. The explainer says so rather than hiding it.",
  },
  {
    icon: <Flame size={20} />,
    chip: "Simulate",
    title: "Forward models: flood and wildfire",
    body:
      "The other analyses measure what happened. These two model what would " +
      "happen. Route a flood over real terrain with a shallow-water solver, or " +
      "spread a wildfire with the same Rothermel physics fire agencies use — " +
      "then scrub through time and open the 3D terrain view to watch it run " +
      "down a valley or up a ridge.",
    tip: "Simulated, never observed — and labelled that way at every step, because a model over real terrain looks exactly as convincing as a measurement.",
    target: "tool-simulation",
    action: { label: "Open forward simulation", run: () => openPanel("simulation") },
  },
  {
    icon: <Ship size={20} />,
    chip: "Maritime",
    title: "Dark vessels",
    body:
      "Big ships must broadcast their position over AIS radio. Radar sees every " +
      "ship regardless. Line the two up and the gap is the interesting part: a " +
      "bright radar return with no transponder anywhere near it.",
    tip: "An unmatched return is not evidence of wrongdoing — small boats are not required to broadcast, and fixed platforms never do. The panel says so.",
    target: "tool-vessels",
    action: { label: "Open dark vessels", run: () => openPanel("vessels") },
  },
  {
    icon: <Radar size={20} />,
    chip: "Millimetres",
    title: "InSAR: measure the ground moving",
    body:
      "The rest of Kairos measures radar brightness. Interferometry measures " +
      "its phase — the shift between two passes — which reveals ground movement " +
      "down to centimetres. The Mexico City scene shows a city sinking into its " +
      "old lakebed, one colour cycle per 2.8 cm.",
    tip: "Published COMET-LiCSAR research products, shown with attribution, not Kairos's own pipeline.",
    target: "tool-insar",
    action: { label: "Open InSAR", run: () => openPanel("insar") },
  },
  {
    icon: <FlaskConical size={20} />,
    chip: "Go deeper",
    title: "Research tools",
    body:
      "Cross-check any result: raw backscatter, true-colour optical, a " +
      "before/after cross-fade, animated time series, population impact — plus " +
      "Signal & Trend, which extracts a full year of real observations over " +
      "your area with trend statistics, a publication chart and a CSV.",
    target: "tool-research",
    action: { label: "Open research tools", run: () => openPanel("research") },
  },
  {
    icon: <Bell size={20} />,
    chip: "Keep watch",
    title: "Monitor an area, or run hundreds",
    body:
      "Sign in and “Watch this area”: Kairos re-checks it on every new " +
      "Sentinel-1 pass and flags fresh detections in Alerts. Got many places " +
      "instead? Batch mode takes a CSV of areas and analysis types, runs them " +
      "all, and exports one CSV back.",
    target: "tool-alerts",
    action: { label: "Open alerts", run: () => openPanel("alerts") },
  },
  {
    icon: <Radio size={20} />,
    chip: "Share",
    title: "Guardian, Live Watch and sharing",
    body:
      "Live Watch is a login-free map of active disasters worldwide. Guardian " +
      "is a login-free mode that spotlights hotspots of illegal mining, " +
      "clearing and fishing for you to review. Any result copies out as a " +
      "reproducible link or an embeddable widget.",
    tip: "Kairos also installs to a phone or iPad home screen from the browser's Share menu.",
    target: "livewatch",
    action: { label: "Open Live Watch", run: openLiveWatch },
  },
  {
    icon: <Telescope size={20} />,
    chip: "Research preview",
    title: "Janus",
    body:
      "Janus is the research layer: an AI that runs real analyses for you, " +
      "mentors a project like an advisor, tracks datasets and citations, and " +
      "exports to LaTeX, Google Docs, a Jupyter notebook or a policy brief. " +
      "It is still in research preview rather than general release.",
    tip: "Access code: janus2026",
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
    } catch {
      /* private mode, fine */
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

  // Locate the highlighted control. Re-measured on resize, and once more
  // shortly after the step changes because panels and rails animate into
  // place — measuring only on the first frame can catch a control mid-slide.
  useLayoutEffect(() => {
    if (!open) return;
    const measure = () => {
      const el = step.target
        ? document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`)
        : null;
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

  // Place the card on whichever side of the target actually has room for it,
  // so it never lands on top of the control it is pointing at.
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

    // Left first: most targets live on the right-hand tool rail.
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
          {/* Dimmer with a hole cut over the highlighted control.
              The SVG is purely visual — an SVG mask changes what is painted,
              not what is hit-tested, so leaving this interactive would have
              swallowed clicks across the whole screen including the hole. The
              four panes below it form the frame around the hole and carry the
              click-to-close instead, which leaves the gap genuinely
              click-through: the highlighted control stays usable while the
              guide is explaining it. */}
          <svg className="pointer-events-none absolute inset-0 h-full w-full">
            <defs>
              <mask id="kairos-tour-mask">
                <rect x="0" y="0" width="100%" height="100%" fill="white" />
                {hole && (
                  <rect
                    x={hole.x}
                    y={hole.y}
                    width={hole.width}
                    height={hole.height}
                    rx="14"
                    fill="black"
                  />
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

          {/* Click-to-close frame. With a hole, four panes around it; without
              one, a single full-screen pane. */}
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
              // Hidden until measured, so it never flashes in the wrong place.
              visibility: pos ? "visible" : "hidden",
            }}
          >
            <div className="flex items-center justify-between px-5 pt-4">
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

            <div className="px-5 pb-2 pt-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 shrink-0 grid place-items-center rounded-2xl bg-raised ring-1 ring-teal/30 text-teal">
                  {step.icon}
                </div>
                <div className="min-w-0">
                  <div className="font-mono text-[9px] tracking-[0.2em] text-amber uppercase">
                    {i + 1} / {STEPS.length} · {step.chip}
                  </div>
                  <h2 className="font-display text-lg text-ink leading-tight mt-0.5">
                    {step.title}
                  </h2>
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
