import { useEffect, useState } from "react";
import { Loader2, Search, Sparkles } from "lucide-react";
import {
  fetchInterpretation,
  fetchRegionalContext,
  type InterpretInput,
} from "../../api/interpret";
import { reverseGeocodeBbox } from "../../lib/geocode";

function renderInsight(text: string) {
  const blocks: React.ReactNode[] = [];
  const lines = text.split("\n");
  let para: string[] = [];
  const flush = (key: string) => {
    if (para.length) {
      blocks.push(
        <p key={key} className="text-[11px] text-ink/90 leading-relaxed">
          {para.join(" ")}
        </p>
      );
      para = [];
    }
  };
  lines.forEach((raw, i) => {
    const line = raw.trim();
    if (line.startsWith("###")) {
      flush(`p${i}`);
      blocks.push(
        <h4
          key={`h${i}`}
          className="font-mono text-[9px] tracking-[0.18em] text-teal uppercase mt-2 first:mt-0"
        >
          {line.replace(/^#+\s*/, "")}
        </h4>
      );
    } else if (!line) {
      flush(`p${i}`);
    } else {

      para.push(line.replace(/\*\*/g, "").replace(/(^|\s)_([^_]+)_/g, "$1$2"));
    }
  });
  flush("end");
  return blocks;
}

export default function ResultInsight({ input }: { input: InterpretInput }) {
  const [text, setText] = useState<string | null>(null);
  const [context, setContext] = useState<string | null>(null);
  const [busy, setBusy] = useState<"explain" | "context" | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [contextNote, setContextNote] = useState<string | null>(null);

  const sig = `${input.analysis_type}|${input.start_date}|${input.end_date}|${input.bbox.join(",")}`;
  useEffect(() => {
    setText(null);
    setContext(null);
    setErr(null);
    setContextNote(null);
  }, [sig]);

  async function withPlace(): Promise<InterpretInput> {
    if (input.place_name) return input;
    const place_name = await reverseGeocodeBbox(input.bbox);
    return place_name ? { ...input, place_name } : input;
  }

  async function explain() {
    setBusy("explain");
    setErr(null);
    try {
      const p = await withPlace();
      const d = await fetchInterpretation(p);
      setText(d.text);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not generate an explanation.");
    } finally {
      setBusy(null);
    }
  }

  async function searchContext() {
    setBusy("context");
    setContextNote(null);
    try {
      const p = await withPlace();
      const d = await fetchRegionalContext(p);
      if (d.available && d.text) setContext(d.text);
      else setContextNote(d.note || "No regional context found.");
    } catch (e) {
      setContextNote(
        e instanceof Error ? e.message : "Regional search is unavailable."
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-2">
      <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
        Understand
      </h3>

      {!text ? (
        <button
          onClick={explain}
          disabled={busy === "explain"}
          title="Plain-language explanation of what this result means"
          className="w-full flex items-center gap-2.5 rounded-xl ring-1 ring-line bg-bg/70 px-3 py-2.5 text-left text-dim hover:text-ink transition disabled:opacity-60"
        >
          <span className="text-amber">
            {busy === "explain" ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Sparkles size={14} />
            )}
          </span>
          <span className="min-w-0">
            <span className="block text-xs text-ink">Explain this result</span>
            <span className="block text-[10px] text-dim leading-tight">
              What it shows, the trend, and likely causes
            </span>
          </span>
        </button>
      ) : (
        <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-3 space-y-1.5">
          {renderInsight(text)}

          {!context ? (
            <button
              onClick={searchContext}
              disabled={busy === "context"}
              title="Search the web for recent news and trends in this region"
              className="mt-2 w-full h-8 rounded-lg text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-teal hover:ring-teal/40 transition disabled:opacity-60"
            >
              {busy === "context" ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Search size={12} />
              )}
              Search regional context
            </button>
          ) : (
            <div className="mt-2 pt-2 border-t border-line space-y-1.5">
              <h4 className="font-mono text-[9px] tracking-[0.18em] text-amber uppercase">
                In the region
              </h4>
              {renderInsight(context)}
            </div>
          )}
          {contextNote && (
            <p className="mt-1 text-[10px] text-dim leading-snug">{contextNote}</p>
          )}
        </div>
      )}

      {err && <p className="text-[10px] text-amber leading-snug px-1">{err}</p>}
    </div>
  );
}
