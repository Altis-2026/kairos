import { useRef, useState } from "react";
import { ArrowUp, Mic, Volume2, VolumeX } from "lucide-react";
import { runQuery } from "../../api/query";
import { useChatStore } from "../../stores/chatStore";
import { useMapStore } from "../../stores/mapStore";
import { usePrefsStore } from "../../stores/prefsStore";
import SuggestionChips from "./SuggestionChips";
import ChatMessages from "./ChatMessage";
import { applyResultToGlobe } from "../../lib/applyResult";
import {
  isSpeechSupported,
  isTTSSupported,
  speak,
  startDictation,
  stopSpeaking,
} from "../../lib/voice";

export { applyResultToGlobe };

let msgId = 0;
const nextId = () => `m${++msgId}-${Date.now()}`;

export default function ChatBar() {
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const dictation = useRef<{ stop: () => void } | null>(null);
  const { addMessage, updateMessage, loading, setLoading } = useChatStore();
  const speakReplies = usePrefsStore((s) => s.speakReplies);
  const toggleSpeakReplies = usePrefsStore((s) => s.toggleSpeakReplies);

  function toggleMic() {
    if (listening) {
      dictation.current?.stop();
      return;
    }
    const handle = startDictation({
      onInterim: (text) => setInput(text),
      onFinal: (text) => void send(text),
      onError: () => setListening(false),
      onEnd: () => setListening(false),
    });
    if (handle) {
      dictation.current = handle;
      setListening(true);
    }
  }

  async function send(text: string) {
    const query = text.trim();
    if (!query || loading) return;
    setInput("");

    const history = useChatStore
      .getState()
      .messages.filter((m) => !m.pending)
      .slice(-8)
      .map((m) => ({ role: m.role, content: m.text }));
    addMessage({ id: nextId(), role: "user", text: query });
    const pendingId = nextId();
    addMessage({
      id: pendingId,
      role: "kairos",
      text: "Querying Sentinel-1 archive…",
      pending: true,
    });
    setLoading(true);

    try {
      const viewport = useMapStore.getState().viewportBbox ?? undefined;
      const res = await runQuery(query, viewport, history);

      if (!res.understood) {
        updateMessage(pendingId, {
          text: res.clarification ?? "Could you tell me more?",
          pending: false,
        });
        return;
      }

      const all = res.results?.length ? res.results : res.result ? [res.result] : [];
      for (const r of all.slice(1).reverse()) applyResultToGlobe(r);
      if (all[0]) applyResultToGlobe(all[0]);
      const params = res.parameters as Record<string, unknown> | null;
      const reasoning =
        params && typeof params.reasoning === "string" ? params.reasoning : undefined;
      const finalText =
        res.explanation ??
        "Analysis complete. The result layer has been added to the globe.";
      updateMessage(pendingId, {
        text: finalText,
        pending: false,
        reasoning,
      });
      if (usePrefsStore.getState().speakReplies) speak(finalText);
    } catch (e) {
      updateMessage(pendingId, {
        text:
          e instanceof Error
            ? e.message
            : "Something went wrong running that analysis.",
        pending: false,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="absolute bottom-5 inset-x-0 z-30 flex flex-col items-center gap-3 px-4 pointer-events-none">
      <ChatMessages />
      <SuggestionChips onPick={send} />
      <div className="w-full max-w-2xl pointer-events-auto">
        <div className="relative">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            placeholder={listening ? "Listening…" : "Ask about this area…"}
            aria-label="Ask Kairos a question about anywhere on Earth"
            disabled={loading}
            className="w-full h-14 pl-6 pr-32 rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line text-[15px] text-ink placeholder-dim outline-none focus:ring-amber/60 shadow-panel transition-shadow disabled:opacity-70"
          />
          {isTTSSupported() && (
            <button
              onClick={() => {
                if (speakReplies) stopSpeaking();
                toggleSpeakReplies();
              }}
              title={speakReplies ? "Stop reading replies aloud" : "Read replies aloud"}
              aria-label={speakReplies ? "Stop reading replies aloud" : "Read replies aloud"}
              className={`absolute right-[5.75rem] top-1/2 -translate-y-1/2 h-9 w-9 grid place-items-center rounded-xl transition ${
                speakReplies ? "text-teal" : "text-dim hover:text-ink"
              }`}
            >
              {speakReplies ? <Volume2 size={16} /> : <VolumeX size={16} />}
            </button>
          )}
          {isSpeechSupported() && (
            <button
              onClick={toggleMic}
              disabled={loading}
              title={listening ? "Stop listening" : "Ask by voice"}
              aria-label={listening ? "Stop listening" : "Ask by voice"}
              className={`absolute right-14 top-1/2 -translate-y-1/2 h-9 w-9 grid place-items-center rounded-xl transition disabled:opacity-40 ${
                listening
                  ? "text-amber animate-pulse-soft"
                  : "text-dim hover:text-ink"
              }`}
            >
              <Mic size={16} />
            </button>
          )}
          <button
            onClick={() => send(input)}
            disabled={loading || !input.trim()}
            title="Run query"
            className="absolute right-3 top-1/2 -translate-y-1/2 h-9 w-9 grid place-items-center rounded-xl bg-amber text-bg hover:brightness-110 transition disabled:opacity-40"
          >
            <ArrowUp size={17} />
          </button>
        </div>
      </div>
    </div>
  );
}
