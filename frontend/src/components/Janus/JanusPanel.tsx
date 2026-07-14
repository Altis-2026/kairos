/**
 * Janus — the research mentor panel.
 *
 * A persistent research project picks up exactly where it left off: the
 * question, the study design, every run, every saved paper. The mentor's
 * tool calls surface as chips inside the conversation, and any analysis it
 * runs can be dropped straight onto the globe.
 *
 * Visual language: standard Kairos panel, but Janus wears amber (the accent
 * color) rather than teal, so mentor moments read differently from data.
 */
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowUp,
  BookMarked,
  BookOpen,
  ChevronDown,
  ChevronLeft,
  ClipboardList,
  Download,
  ExternalLink,
  FlaskConical,
  Globe2,
  GraduationCap,
  Loader2,
  Mic,
  Plus,
  RadioTower,
  ShieldCheck,
  Sparkles,
  ScrollText,
  Telescope,
  Trash2,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";
import { useJanusStore } from "../../stores/janusStore";
import { applyResultToGlobe } from "../../lib/applyResult";
import { downloadNotebook, downloadPack, fetchPeerReview } from "../../api/janus";
import { timeAgo } from "../../api/feed";
import {
  isSpeechSupported,
  isTTSSupported,
  speak,
  startDictation,
  stopSpeaking,
} from "../../lib/voice";
import type {
  ConfounderReport,
  Hypothesis,
  Insight,
  JanusMessage,
  JanusMode,
  JanusProject,
  StudyDesign,
  ToolEvent,
} from "../../api/janus";

const VOICE_OUT_KEY = "kairos_janus_voice_out";

const STAGES: JanusProject["stage"][] = [
  "exploring",
  "designing",
  "analyzing",
  "validating",
  "writing",
];

const MODES: { id: JanusMode; label: string; hint: string }[] = [
  { id: "mentor", label: "Mentor", hint: "Teach me and think with me" },
  { id: "design", label: "Design", hint: "Lock down the study design" },
  { id: "review", label: "Review", hint: "Critique my work like a reviewer" },
];

/** Markdown-lite: ### headers, "- " bullets, blank-line paragraphs. */
function renderMentorText(text: string) {
  const blocks: React.ReactNode[] = [];
  let para: string[] = [];
  let bullets: string[] = [];
  const flush = (key: string) => {
    if (bullets.length) {
      blocks.push(
        <ul key={`u${key}`} className="space-y-1 pl-1">
          {bullets.map((b, i) => (
            <li key={i} className="flex gap-2 text-xs leading-relaxed">
              <span className="text-amber shrink-0 mt-[3px]">·</span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
      );
      bullets = [];
    }
    if (para.length) {
      blocks.push(
        <p key={`p${key}`} className="text-xs leading-relaxed">
          {para.join(" ")}
        </p>
      );
      para = [];
    }
  };
  text.split("\n").forEach((raw, i) => {
    const line = raw.trim().replace(/\*\*/g, "");
    if (line.startsWith("###")) {
      flush(`${i}`);
      blocks.push(
        <h4
          key={`h${i}`}
          className="font-mono text-[9px] tracking-[0.18em] text-amber uppercase mt-2.5 first:mt-0"
        >
          {line.replace(/^#+\s*/, "")}
        </h4>
      );
    } else if (line.startsWith("- ")) {
      if (para.length) flush(`${i}`);
      bullets.push(line.slice(2));
    } else if (!line) {
      flush(`${i}`);
    } else {
      if (bullets.length) flush(`${i}`);
      para.push(line);
    }
  });
  flush("end");
  return blocks;
}

function StagePips({ stage }: { stage: JanusProject["stage"] }) {
  const idx = STAGES.indexOf(stage);
  return (
    <div className="flex items-center gap-1" title={`Stage: ${stage}`}>
      {STAGES.map((s, i) => (
        <span
          key={s}
          className={`h-1 rounded-full transition-all ${
            i < idx
              ? "w-2 bg-amber/50"
              : i === idx
              ? "w-4 bg-amber"
              : "w-2 bg-line"
          }`}
        />
      ))}
      <span className="ml-1.5 font-mono text-[9px] tracking-wider text-dim uppercase">
        {stage}
      </span>
    </div>
  );
}

function DesignCard({ design }: { design: StudyDesign }) {
  const [open, setOpen] = useState(false);
  const rows: [string, string][] = [];
  if (design.hypothesis) rows.push(["Hypothesis", design.hypothesis]);
  if (design.place) rows.push(["Place", design.place]);
  if (design.bbox) rows.push(["AOI", design.bbox.map((n) => n.toFixed(2)).join(", ")]);
  if (design.start_date && design.end_date)
    rows.push(["Window", `${design.start_date} to ${design.end_date}`]);
  if (design.analysis_types?.length)
    rows.push(["Methods", design.analysis_types.join(", ")]);
  if (design.confounders?.length)
    rows.push(["Confounders", design.confounders.join("; ")]);
  if (design.validation_plan) rows.push(["Validation", design.validation_plan]);
  if (rows.length === 0) return null;

  return (
    <div className="rounded-xl bg-bg/70 ring-1 ring-amber/25">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-left"
      >
        <span className="flex items-center gap-2 font-mono text-[9px] tracking-[0.18em] text-amber uppercase">
          <ClipboardList size={11} />
          Study design · {rows.length} element{rows.length > 1 ? "s" : ""}
        </span>
        <ChevronDown
          size={12}
          className={`text-dim transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="px-3 pb-2.5 space-y-1.5">
          {rows.map(([label, value]) => (
            <div key={label} className="text-[11px] leading-snug">
              <span className="text-dim">{label}: </span>
              <span className="text-ink/90">{value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const HYP_TONE: Record<Hypothesis["status"], string> = {
  open: "text-dim ring-line",
  supported: "text-teal ring-teal/40 bg-teal/10",
  refuted: "text-[#FF3B5C] ring-[#FF3B5C]/40 bg-[#FF3B5C]/10",
  inconclusive: "text-amber ring-amber/40 bg-amber/10",
};

function ResearchLog({ hypotheses }: { hypotheses: Hypothesis[] }) {
  const [open, setOpen] = useState(false);
  if (hypotheses.length === 0) return null;
  return (
    <div className="rounded-xl bg-bg/70 ring-1 ring-line">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-left"
      >
        <span className="flex items-center gap-2 font-mono text-[9px] tracking-[0.18em] text-amber uppercase">
          <ScrollText size={11} />
          Research log · {hypotheses.length} hypothes
          {hypotheses.length > 1 ? "es" : "is"}
        </span>
        <ChevronDown
          size={12}
          className={`text-dim transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="px-3 pb-2.5 space-y-2">
          {hypotheses.map((h) => (
            <div key={h.id} className="text-[11px] leading-snug">
              <div className="flex items-start gap-1.5">
                <span
                  className={`shrink-0 rounded px-1 py-0.5 font-mono text-[8px] uppercase tracking-wider ring-1 ${
                    HYP_TONE[h.status]
                  }`}
                >
                  {h.status}
                </span>
                <span className="flex-1 text-ink/90">{h.statement}</span>
              </div>
              {h.evidence && (
                <div className="mt-0.5 pl-1 text-dim">{h.evidence}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PeerReviewModal({
  markdown,
  loading,
  onClose,
}: {
  markdown: string | null;
  loading: boolean;
  onClose: () => void;
}) {
  return (
    <div
      className="absolute inset-0 z-50 grid place-items-center bg-bg/70 backdrop-blur-sm p-4 rounded-2xl"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-h-full flex flex-col rounded-xl bg-surface ring-1 ring-line shadow-panel"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-line">
          <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-amber">
            <ShieldCheck size={13} />
            PEER REVIEW
          </span>
          <button onClick={onClose} className="text-dim hover:text-ink transition">
            <X size={14} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
          {loading ? (
            <div className="flex items-center gap-2 text-dim text-xs py-6 justify-center">
              <Loader2 size={14} className="animate-spin" />
              Janus is reviewing the whole project…
            </div>
          ) : (
            <div className="space-y-1.5">{renderMentorText(markdown || "")}</div>
          )}
        </div>
      </div>
    </div>
  );
}

const CONCERN_TONE: Record<ConfounderReport["overall_concern"], string> = {
  high: "text-[#FF3B5C] ring-[#FF3B5C]/30",
  some: "text-amber ring-amber/30",
  low: "text-teal ring-teal/30",
};

function EventChip({ event }: { event: ToolEvent }) {
  const [showPapers, setShowPapers] = useState(false);
  const [showConcept, setShowConcept] = useState(false);
  const [showConf, setShowConf] = useState(false);
  const tone =
    event.status === "error"
      ? "text-[#FF3B5C] ring-[#FF3B5C]/30"
      : event.status === "empty"
      ? "text-dim ring-line"
      : "text-teal ring-teal/30";

  return (
    <div className="space-y-1.5">
      <div
        className={`inline-flex max-w-full items-center gap-2 rounded-lg bg-bg/70 ring-1 px-2.5 py-1.5 font-mono text-[10px] ${tone}`}
      >
        <span className="truncate">{event.label}</span>
        {event.result && (
          <button
            onClick={() => applyResultToGlobe(event.result!)}
            title="Show this result on the globe"
            className="flex shrink-0 items-center gap-1 rounded-md bg-teal/15 px-1.5 py-0.5 text-teal hover:bg-teal/25 transition"
          >
            <Globe2 size={10} />
            globe
          </button>
        )}
        {event.papers && event.papers.length > 0 && (
          <button
            onClick={() => setShowPapers(!showPapers)}
            className="shrink-0 rounded-md bg-raised px-1.5 py-0.5 text-dim hover:text-ink transition"
          >
            {showPapers ? "hide" : "view"}
          </button>
        )}
        {event.concept && (
          <button
            onClick={() => setShowConcept(!showConcept)}
            className="shrink-0 rounded-md bg-raised px-1.5 py-0.5 text-dim hover:text-ink transition"
          >
            {showConcept ? "hide" : "view"}
          </button>
        )}
        {event.confounders && (
          <button
            onClick={() => setShowConf(!showConf)}
            className="shrink-0 rounded-md bg-raised px-1.5 py-0.5 text-dim hover:text-ink transition"
          >
            {showConf ? "hide" : "view"}
          </button>
        )}
      </div>
      {showConf && event.confounders && (
        <div
          className={`rounded-lg bg-bg/60 ring-1 px-2.5 py-2 space-y-1.5 ${
            CONCERN_TONE[event.confounders.overall_concern]
          }`}
        >
          <div className="flex items-center gap-1.5 font-mono text-[9px] tracking-[0.16em] uppercase">
            <FlaskConical size={11} />
            {event.confounders.overall_concern} concern of a false-positive driver
          </div>
          {event.confounders.findings.map((f, i) => (
            <div key={i} className="text-[11px] leading-relaxed text-ink/90">
              {f.finding}
            </div>
          ))}
        </div>
      )}
      {showConcept && event.concept && (
        <div className="rounded-lg bg-bg/60 ring-1 ring-line px-2.5 py-2 space-y-1.5">
          <div className="text-[11px] leading-relaxed text-ink/90">
            {event.concept.explanation}
          </div>
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {event.concept.resources.map((r, i) => (
              <a
                key={i}
                href={r.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 rounded-md bg-raised px-1.5 py-0.5 font-mono text-[9px] text-dim hover:text-teal transition"
              >
                {r.name}
                <ExternalLink size={9} />
              </a>
            ))}
          </div>
        </div>
      )}
      {showPapers && event.papers && (
        <div className="space-y-1.5 pl-1">
          {event.papers.map((p, i) => (
            <div key={i} className="rounded-lg bg-bg/60 ring-1 ring-line px-2.5 py-2">
              <div className="flex items-start gap-1.5">
                <span className="flex-1 text-[11px] leading-snug text-ink/90">
                  {p.title}
                </span>
                {p.doi && (
                  <a
                    href={p.doi}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 text-dim hover:text-teal transition"
                    title="Open paper"
                  >
                    <ExternalLink size={11} />
                  </a>
                )}
              </div>
              <div className="mt-0.5 font-mono text-[9px] text-dim">
                {p.authors} {p.year ? `· ${p.year}` : ""}
                {p.venue ? ` · ${p.venue}` : ""} · cited {p.cited_by}×
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ m }: { m: JanusMessage }) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-xl bg-raised px-3 py-2 text-xs leading-relaxed text-ink">
          {m.content}
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-start">
      <div className="max-w-[92%] space-y-2">
        {m.tool_events.map((ev, i) => (
          <EventChip key={i} event={ev} />
        ))}
        <div className="rounded-xl bg-bg/80 ring-1 ring-line px-3 py-2.5 space-y-1.5 text-ink/95">
          {renderMentorText(m.content)}
        </div>
      </div>
    </div>
  );
}

function InsightBanner({
  insight,
  onAct,
  onDismiss,
}: {
  insight: Insight;
  onAct: (insight: Insight) => void;
  onDismiss: (id: number) => void;
}) {
  return (
    <div className="rounded-xl bg-amber/10 ring-1 ring-amber/40 px-3 py-2.5 space-y-2">
      <div className="flex items-start gap-2">
        <RadioTower size={13} className="mt-0.5 shrink-0 text-amber animate-pulse-soft" />
        <div className="flex-1 text-[11px] leading-relaxed text-ink/90">
          <span className="font-mono text-[9px] tracking-[0.18em] text-amber uppercase">
            Janus noticed
          </span>
          <p className="mt-0.5">{insight.content}</p>
        </div>
        <button
          onClick={() => onDismiss(insight.id)}
          title="Dismiss"
          className="shrink-0 text-dim hover:text-ink transition"
        >
          <X size={12} />
        </button>
      </div>
      {insight.action?.label && (
        <button
          onClick={() => onAct(insight)}
          className="w-full h-8 flex items-center justify-center gap-1.5 rounded-lg bg-amber text-bg text-[11px] font-medium hover:brightness-110 transition"
        >
          <Sparkles size={11} />
          {insight.action.label}
        </button>
      )}
    </div>
  );
}

export default function JanusPanel({ onClose }: { onClose: () => void }) {
  const {
    available,
    entitlements,
    projects,
    curricula,
    bundle,
    loadingHome,
    openingId,
    sending,
    watchBusy,
    error,
    loadHome,
    open,
    startProject,
    send,
    setWatch,
    dismiss,
    backToList,
    remove,
    clearError,
  } = useJanusStore();

  const [draft, setDraft] = useState("");
  const [mode, setMode] = useState<JanusMode>("mentor");
  const [newQuestion, setNewQuestion] = useState("");
  const [showBiblio, setShowBiblio] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportingNb, setExportingNb] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewText, setReviewText] = useState<string | null>(null);
  const [listening, setListening] = useState(false);
  const [voiceOut, setVoiceOut] = useState(() => {
    try {
      return localStorage.getItem(VOICE_OUT_KEY) === "1";
    } catch {
      return false;
    }
  });
  const endRef = useRef<HTMLDivElement>(null);
  const dictationRef = useRef<{ stop: () => void } | null>(null);
  const spokenRef = useRef<number | null>(null);

  const voiceInAvailable = isSpeechSupported();
  const voiceOutAvailable = isTTSSupported();
  const watched = !!bundle?.project.watched;

  useEffect(() => {
    if (!bundle) void loadHome();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [bundle?.messages.length, sending]);

  // Read new mentor replies aloud when voice output is on. Guarded by message
  // id so re-renders don't re-speak, and so we never speak the loaded history.
  useEffect(() => {
    if (!voiceOut || !bundle || sending) return;
    const msgs = bundle.messages;
    const last = msgs[msgs.length - 1];
    if (!last || last.role !== "assistant") return;
    if (spokenRef.current === last.id) return;
    spokenRef.current = last.id;
    speak(last.content);
  }, [bundle?.messages, voiceOut, sending, bundle]);

  // Stop any audio / mic when the panel unmounts.
  useEffect(() => {
    return () => {
      stopSpeaking();
      dictationRef.current?.stop();
    };
  }, []);

  function submit() {
    const text = draft.trim();
    if (!text || sending) return;
    setDraft("");
    void send(text, mode);
  }

  function toggleVoiceOut() {
    const next = !voiceOut;
    setVoiceOut(next);
    if (!next) stopSpeaking();
    try {
      localStorage.setItem(VOICE_OUT_KEY, next ? "1" : "0");
    } catch {
      /* private mode */
    }
  }

  function toggleMic() {
    if (listening) {
      dictationRef.current?.stop();
      return;
    }
    stopSpeaking();
    const handle = startDictation({
      onInterim: (text) => setDraft(text),
      onFinal: (text) => setDraft(text),
      onError: () => setListening(false),
      onEnd: () => {
        setListening(false);
        dictationRef.current = null;
      },
    });
    if (handle) {
      dictationRef.current = handle;
      setListening(true);
    }
  }

  async function exportPack() {
    if (!bundle || exporting) return;
    setExporting(true);
    try {
      await downloadPack(bundle.project.id, bundle.project.title);
    } catch (e) {
      useJanusStore.setState({
        error: e instanceof Error ? e.message : "Export failed.",
      });
    } finally {
      setExporting(false);
    }
  }

  async function exportNotebook() {
    if (!bundle || exportingNb) return;
    setExportingNb(true);
    try {
      await downloadNotebook(bundle.project.id, bundle.project.title);
    } catch (e) {
      useJanusStore.setState({
        error: e instanceof Error ? e.message : "Export failed.",
      });
    } finally {
      setExportingNb(false);
    }
  }

  async function runPeerReview() {
    if (!bundle || reviewLoading) return;
    setReviewOpen(true);
    setReviewLoading(true);
    setReviewText(null);
    try {
      const res = await fetchPeerReview(bundle.project.id);
      setReviewText(res.markdown);
    } catch (e) {
      setReviewText(
        `### Review failed\n${e instanceof Error ? e.message : "Try again."}`
      );
    } finally {
      setReviewLoading(false);
    }
  }

  function actOnInsight(insight: Insight) {
    const action = insight.action;
    if (!action) return;
    dismiss(insight.id);
    // Keep the mentor in the loop: ask it to re-run and interpret, rather than
    // silently dropping a raster on the globe. It has the params in context.
    const label = action.label || "the suggested analysis";
    void send(
      `Yes, please ${label.toLowerCase()} and tell me what changed since last time.`,
      "mentor"
    );
  }

  function startFromQuestion() {
    const q = newQuestion.trim();
    if (!q) return;
    const title = q.length > 60 ? `${q.slice(0, 57)}…` : q;
    setNewQuestion("");
    void startProject(title, q, null);
  }

  const header = (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.22em] text-dim">
        <Telescope size={13} className="text-amber" />
        JANUS · RESEARCH MENTOR
      </div>
      <div className="flex items-center gap-2">
        {entitlements && (
          <span
            title={entitlements.blurb}
            className="rounded-md bg-amber/10 ring-1 ring-amber/30 px-1.5 py-0.5 font-mono text-[9px] tracking-wider text-amber"
          >
            {entitlements.tier_name.toUpperCase()}
          </span>
        )}
        <button
          onClick={onClose}
          className="text-dim hover:text-ink transition-colors"
          title="Close"
        >
          <X size={15} />
        </button>
      </div>
    </div>
  );

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute right-20 top-20 bottom-24 z-40 w-[26rem] max-w-[calc(100vw-7rem)] rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 flex flex-col gap-3"
    >
      {header}

      {available === false && (
        <p className="text-xs leading-relaxed text-dim">
          Janus needs the AI provider configured on the backend
          (OPENROUTER_API_KEY). Everything else in Kairos still works.
        </p>
      )}

      {/* ---------- Home: projects + new project ---------- */}
      {available !== false && !bundle && (
        <div className="min-h-0 flex-1 overflow-y-auto space-y-4 pr-0.5">
          <p className="text-xs leading-relaxed text-dim">
            A mentor that works with you like a PhD scientist: it teaches the
            craft, designs studies with you, runs real analyses mid-sentence,
            and pushes back on weak reasoning.
          </p>

          {entitlements && entitlements.skills.length > 0 && (
            <div className="rounded-xl bg-bg/70 ring-1 ring-line px-3 py-2.5">
              <div className="flex items-center gap-1.5 font-mono text-[9px] tracking-[0.18em] text-amber uppercase">
                <GraduationCap size={11} />
                What Janus knows you can do
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {entitlements.skills.slice(0, 10).map((s) => (
                  <span
                    key={s.skill}
                    title={s.note || undefined}
                    className={`rounded-md px-1.5 py-0.5 text-[10px] ring-1 ${
                      s.level === "confident"
                        ? "text-teal ring-teal/40 bg-teal/10"
                        : s.level === "practiced"
                        ? "text-amber ring-amber/30"
                        : "text-dim ring-line"
                    }`}
                  >
                    {s.skill}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-[10px] leading-snug text-dim">
                Janus remembers this across every project and teaches to your
                gaps.
              </p>
            </div>
          )}

          {loadingHome && (
            <div className="flex items-center gap-2 text-dim text-xs">
              <Loader2 size={13} className="animate-spin" /> Loading…
            </div>
          )}

          {projects.length > 0 && (
            <div className="space-y-2">
              <div className="font-mono text-[9px] tracking-[0.18em] text-dim uppercase">
                Your projects
              </div>
              {projects.map((p) => (
                <div
                  key={p.id}
                  className="group flex items-center gap-2 rounded-xl bg-bg/70 ring-1 ring-line px-3 py-2.5 hover:ring-amber/40 transition"
                >
                  <button
                    onClick={() => open(p.id)}
                    disabled={openingId !== null}
                    className="min-w-0 flex-1 text-left"
                  >
                    <div className="truncate text-xs text-ink">{p.title}</div>
                    <div className="mt-1 flex items-center gap-2">
                      <StagePips stage={p.stage} />
                      <span className="font-mono text-[9px] text-dim">
                        {timeAgo(p.updated_at)}
                      </span>
                    </div>
                  </button>
                  {openingId === p.id ? (
                    <Loader2 size={13} className="animate-spin text-dim" />
                  ) : (
                    <button
                      onClick={() => remove(p.id)}
                      title="Delete project"
                      className="opacity-0 group-hover:opacity-100 text-dim hover:text-[#FF3B5C] transition"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="space-y-2">
            <div className="font-mono text-[9px] tracking-[0.18em] text-dim uppercase">
              Start from a question
            </div>
            <textarea
              value={newQuestion}
              onChange={(e) => setNewQuestion(e.target.value)}
              placeholder="e.g. Is illegal mining growing along the Madre de Dios river?"
              rows={2}
              className="w-full resize-none rounded-xl bg-bg px-3 py-2.5 text-xs text-ink ring-1 ring-line placeholder:text-dim focus:ring-amber/60 outline-none"
            />
            <button
              onClick={startFromQuestion}
              disabled={!newQuestion.trim() || openingId !== null}
              className="w-full h-9 flex items-center justify-center gap-1.5 rounded-xl bg-amber text-bg text-xs font-medium hover:brightness-110 transition disabled:opacity-50"
            >
              {openingId === -1 ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Plus size={13} />
              )}
              Start research project
            </button>
          </div>

          {curricula.length > 0 && (
            <div className="space-y-2">
              <div className="font-mono text-[9px] tracking-[0.18em] text-dim uppercase">
                Or take a course
              </div>
              {curricula.map((c) => (
                <button
                  key={c.id}
                  onClick={() => startProject(c.title, "", c.id)}
                  disabled={openingId !== null}
                  className="w-full rounded-xl bg-bg/70 ring-1 ring-line px-3 py-2.5 text-left hover:ring-amber/40 transition"
                >
                  <div className="flex items-center gap-2 text-xs text-ink">
                    <GraduationCap size={13} className="text-amber shrink-0" />
                    {c.title}
                    <span className="ml-auto font-mono text-[9px] text-dim">
                      {c.sessions.length} sessions
                    </span>
                  </div>
                  <div className="mt-1 text-[11px] leading-snug text-dim">
                    {c.outcome}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ---------- Conversation ---------- */}
      {available !== false && bundle && (
        <>
          <div className="flex items-center gap-2">
            <button
              onClick={backToList}
              title="All projects"
              className="text-dim hover:text-ink transition"
            >
              <ChevronLeft size={15} />
            </button>
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs text-ink">
                {bundle.project.title}
              </div>
              <StagePips stage={bundle.project.stage} />
            </div>
            <button
              onClick={() => setWatch(!watched)}
              disabled={watchBusy}
              title={
                watched
                  ? "Monitoring on: Janus checks for new Sentinel-1 passes"
                  : "Watch this study area for new satellite passes"
              }
              className={`flex items-center gap-1 rounded-lg px-2 py-1 font-mono text-[10px] ring-1 transition disabled:opacity-50 ${
                watched
                  ? "text-amber ring-amber/40 bg-amber/10"
                  : "text-dim ring-line hover:text-ink"
              }`}
            >
              {watchBusy ? (
                <Loader2 size={11} className="animate-spin" />
              ) : (
                <RadioTower size={11} />
              )}
              {watched ? "Watching" : "Watch"}
            </button>
            {bundle.bibliography.length > 0 && (
              <button
                onClick={() => setShowBiblio(!showBiblio)}
                title="Bibliography"
                className={`flex items-center gap-1 rounded-lg px-2 py-1 font-mono text-[10px] ring-1 transition ${
                  showBiblio
                    ? "text-amber ring-amber/40 bg-amber/10"
                    : "text-dim ring-line hover:text-ink"
                }`}
              >
                <BookMarked size={11} />
                {bundle.bibliography.length}
              </button>
            )}
          </div>

          {bundle.insights.length > 0 && (
            <div className="space-y-2">
              {bundle.insights.map((ins) => (
                <InsightBanner
                  key={ins.id}
                  insight={ins}
                  onAct={actOnInsight}
                  onDismiss={dismiss}
                />
              ))}
            </div>
          )}

          <DesignCard design={bundle.project.design} />

          <ResearchLog hypotheses={bundle.hypotheses} />

          {/* Deliverables: the artifacts a researcher takes away. */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={exportPack}
              disabled={exporting}
              title="Reproducibility pack: a Markdown methods report"
              className="flex flex-1 items-center justify-center gap-1 rounded-lg px-2 py-1.5 font-mono text-[9px] tracking-wider ring-1 ring-line text-dim hover:text-ink transition disabled:opacity-50"
            >
              {exporting ? (
                <Loader2 size={11} className="animate-spin" />
              ) : (
                <Download size={11} />
              )}
              PACK
            </button>
            <button
              onClick={exportNotebook}
              disabled={exportingNb}
              title="Runnable Python Earth Engine script that reproduces every analysis"
              className="flex flex-1 items-center justify-center gap-1 rounded-lg px-2 py-1.5 font-mono text-[9px] tracking-wider ring-1 ring-line text-dim hover:text-ink transition disabled:opacity-50"
            >
              {exportingNb ? (
                <Loader2 size={11} className="animate-spin" />
              ) : (
                <ScrollText size={11} />
              )}
              CODE
            </button>
            <button
              onClick={runPeerReview}
              disabled={reviewLoading}
              title="Generate a formal peer-review report of the whole project"
              className="flex flex-1 items-center justify-center gap-1 rounded-lg px-2 py-1.5 font-mono text-[9px] tracking-wider ring-1 ring-amber/30 text-amber hover:bg-amber/10 transition disabled:opacity-50"
            >
              {reviewLoading ? (
                <Loader2 size={11} className="animate-spin" />
              ) : (
                <ShieldCheck size={11} />
              )}
              REVIEW
            </button>
          </div>

          {showBiblio && (
            <div className="max-h-36 overflow-y-auto rounded-xl bg-bg/70 ring-1 ring-line p-2.5 space-y-2">
              {bundle.bibliography.map((r) => (
                <div key={r.id} className="text-[11px] leading-snug">
                  <div className="flex items-start gap-1.5">
                    <ScrollText size={11} className="mt-0.5 shrink-0 text-amber" />
                    <span className="flex-1 text-ink/90">
                      {r.title}
                      {r.year ? ` (${r.year})` : ""}
                    </span>
                    {r.url && (
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noreferrer"
                        className="shrink-0 text-dim hover:text-teal"
                      >
                        <ExternalLink size={11} />
                      </a>
                    )}
                  </div>
                  {r.note && <div className="pl-4 text-dim">{r.note}</div>}
                </div>
              ))}
            </div>
          )}

          <div className="min-h-0 flex-1 overflow-y-auto space-y-3 pr-0.5">
            {bundle.messages.map((m) => (
              <MessageBubble key={m.id} m={m} />
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="relative overflow-hidden scanline rounded-xl bg-bg/80 ring-1 ring-amber/30 px-3 py-2 font-mono text-[10px] text-amber">
                  Janus is working — it may run analyses or search literature…
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-xl bg-[#FF3B5C]/10 ring-1 ring-[#FF3B5C]/30 px-3 py-2 text-[11px] text-[#FF3B5C]">
              <span className="flex-1">{error}</span>
              <button onClick={clearError} className="shrink-0">
                <X size={12} />
              </button>
            </div>
          )}

          <div className="space-y-2">
            <div className="flex items-center gap-1">
              {MODES.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setMode(m.id)}
                  title={m.hint}
                  className={`flex-1 h-7 rounded-lg font-mono text-[10px] tracking-wider ring-1 transition ${
                    mode === m.id
                      ? "bg-amber/15 text-amber ring-amber/40"
                      : "text-dim ring-line hover:text-ink"
                  }`}
                >
                  {m.label.toUpperCase()}
                </button>
              ))}
              {voiceOutAvailable && (
                <button
                  onClick={toggleVoiceOut}
                  title={
                    voiceOut
                      ? "Voice replies on: Janus reads answers aloud"
                      : "Voice replies off"
                  }
                  className={`h-7 w-7 shrink-0 grid place-items-center rounded-lg ring-1 transition ${
                    voiceOut
                      ? "bg-amber/15 text-amber ring-amber/40"
                      : "text-dim ring-line hover:text-ink"
                  }`}
                >
                  {voiceOut ? <Volume2 size={13} /> : <VolumeX size={13} />}
                </button>
              )}
            </div>
            <div className="flex items-end gap-2">
              {voiceInAvailable && (
                <button
                  onClick={toggleMic}
                  disabled={sending}
                  title={listening ? "Stop dictation" : "Speak your message"}
                  className={`h-9 w-9 shrink-0 grid place-items-center rounded-xl ring-1 transition disabled:opacity-50 ${
                    listening
                      ? "bg-[#FF3B5C]/15 text-[#FF3B5C] ring-[#FF3B5C]/40 animate-pulse-soft"
                      : "text-dim ring-line hover:text-ink"
                  }`}
                >
                  <Mic size={14} />
                </button>
              )}
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
                placeholder={
                  listening
                    ? "Listening…"
                    : mode === "design"
                    ? "Describe what you want to study…"
                    : mode === "review"
                    ? "Paste a claim or draft for review…"
                    : "Ask, answer, or think out loud…"
                }
                rows={2}
                className="min-w-0 flex-1 resize-none rounded-xl bg-bg px-3 py-2.5 text-xs text-ink ring-1 ring-line placeholder:text-dim focus:ring-amber/60 outline-none"
              />
              <button
                onClick={submit}
                disabled={!draft.trim() || sending}
                title="Send (Enter)"
                className="h-9 w-9 shrink-0 grid place-items-center rounded-xl bg-amber text-bg hover:brightness-110 transition disabled:opacity-50"
              >
                {sending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <ArrowUp size={14} />
                )}
              </button>
            </div>
            {bundle.project.curriculum_id && (
              <div className="flex items-center gap-1.5 font-mono text-[9px] text-dim">
                <BookOpen size={10} className="text-amber" />
                Course project: Janus teaches the next session each time you're
                ready.
              </div>
            )}
          </div>

          {reviewOpen && (
            <PeerReviewModal
              markdown={reviewText}
              loading={reviewLoading}
              onClose={() => setReviewOpen(false)}
            />
          )}
        </>
      )}
    </motion.aside>
  );
}
