import { useRef, useState } from "react";
import { ArrowUp, MessageSquare, Mic, Square, Volume2, VolumeX } from "lucide-react";
import { useChatStore } from "../../stores/chatStore";
import { usePrefsStore } from "../../stores/prefsStore";
import { ask, stopAsking } from "../../lib/chat";
import { speechLang, useT } from "../../lib/i18n";
import { isSpeechSupported, isTTSSupported, startDictation, stopSpeaking } from "../../lib/voice";
import SuggestionChips from "./SuggestionChips";
import ChatMessages from "./ChatMessage";

export default function ChatBar() {
  const t = useT();
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const dictation = useRef<{ stop: () => void } | null>(null);
  const loading = useChatStore((s) => s.loading);
  const panelOpen = useChatStore((s) => s.panelOpen);
  const messageCount = useChatStore((s) => s.messages.length);
  const setPanelOpen = useChatStore((s) => s.setPanelOpen);
  const speakReplies = usePrefsStore((s) => s.speakReplies);
  const toggleSpeakReplies = usePrefsStore((s) => s.toggleSpeakReplies);
  const locale = usePrefsStore((s) => s.locale);

  function send(text: string) {
    if (!text.trim() || loading) return;
    setInput("");
    void ask(text);
  }

  function toggleMic() {
    if (listening) {
      dictation.current?.stop();
      return;
    }
    const handle = startDictation({
      lang: speechLang(locale),
      onInterim: setInput,
      onFinal: send,
      onError: () => setListening(false),
      onEnd: () => setListening(false),
    });
    if (handle) {
      dictation.current = handle;
      setListening(true);
    }
  }

  const iconButton =
    "h-9 w-9 grid place-items-center rounded-xl transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber/70";

  return (
    <div className="absolute bottom-5 inset-x-0 z-30 flex flex-col items-center gap-3 px-4 pointer-events-none">
      <ChatMessages />
      {!panelOpen && messageCount > 0 && (
        <button
          onClick={() => setPanelOpen(true)}
          className="pointer-events-auto inline-flex items-center gap-2 h-8 px-3.5 rounded-full bg-surface/95 ring-1 ring-line text-xs text-dim hover:text-ink transition"
        >
          <MessageSquare size={13} className="text-teal" />
          {t("showConversation")}
        </button>
      )}
      <SuggestionChips onPick={send} />
      <form
        className="w-full max-w-2xl pointer-events-auto"
        data-tour="ask"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <div className="relative">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={listening ? t("listening") : t("askPlaceholder")}
            aria-label={t("askPlaceholder")}
            enterKeyHint="send"
            className="w-full h-14 pl-6 pr-36 rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line text-[15px] text-ink placeholder-dim outline-none focus:ring-amber/60 shadow-panel transition-shadow"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
            {isTTSSupported() && (
              <button
                type="button"
                onClick={() => {
                  if (speakReplies) stopSpeaking();
                  toggleSpeakReplies();
                }}
                title={speakReplies ? t("stopReading") : t("readAloud")}
                aria-label={speakReplies ? t("stopReading") : t("readAloud")}
                aria-pressed={speakReplies}
                className={`${iconButton} ${speakReplies ? "text-teal" : "text-dim hover:text-ink"}`}
              >
                {speakReplies ? <Volume2 size={16} /> : <VolumeX size={16} />}
              </button>
            )}
            {isSpeechSupported() && (
              <button
                type="button"
                onClick={toggleMic}
                disabled={loading}
                title={listening ? t("stopListening") : t("askByVoice")}
                aria-label={listening ? t("stopListening") : t("askByVoice")}
                aria-pressed={listening}
                className={`${iconButton} disabled:opacity-40 ${
                  listening ? "text-amber animate-pulse-soft" : "text-dim hover:text-ink"
                }`}
              >
                <Mic size={16} />
              </button>
            )}
            {loading ? (
              <button
                type="button"
                onClick={stopAsking}
                title={t("stop")}
                aria-label={t("stop")}
                className={`${iconButton} bg-raised text-ink ring-1 ring-line hover:ring-amber/60`}
              >
                <Square size={13} fill="currentColor" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                title={t("send")}
                aria-label={t("send")}
                className={`${iconButton} bg-amber text-bg hover:brightness-110 disabled:opacity-40`}
              >
                <ArrowUp size={17} />
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
