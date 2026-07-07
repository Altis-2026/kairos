import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useChatStore } from "../../stores/chatStore";

export default function ChatMessages() {
  const { messages, panelOpen, setPanelOpen } = useChatStore();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!panelOpen || messages.length === 0) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 12 }}
        className="w-full max-w-2xl max-h-60 sm:max-h-72 overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-3 pointer-events-auto"
      >
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
            KAIROS · CONVERSATION
          </span>
          <button
            onClick={() => setPanelOpen(false)}
            className="text-dim hover:text-ink transition-colors"
            title="Hide conversation"
          >
            <X size={14} />
          </button>
        </div>
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
                m.role === "user"
                  ? "bg-raised text-ink"
                  : m.pending
                  ? "relative overflow-hidden scanline bg-bg/80 text-teal ring-1 ring-teal/30 font-mono text-xs"
                  : "bg-bg/80 text-ink ring-1 ring-line"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </motion.div>
    </AnimatePresence>
  );
}
