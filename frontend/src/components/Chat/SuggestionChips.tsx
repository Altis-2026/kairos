/** Example queries that demonstrate what Kairos can do — one click to run. */
import { useChatStore } from "../../stores/chatStore";

const SUGGESTIONS = [
  "Flooding in Bangladesh — August 2024",
  "Ships in the Strait of Hormuz this week",
  "Deforestation in Rondônia, Brazil this year",
  "Sea ice extent near Svalbard last month",
];

export default function SuggestionChips({
  onPick,
}: {
  onPick: (text: string) => void;
}) {
  const loading = useChatStore((s) => s.loading);
  const hasMessages = useChatStore((s) => s.messages.length > 0);

  if (hasMessages) return null;

  return (
    <div className="flex flex-wrap justify-center gap-2 pointer-events-auto">
      {SUGGESTIONS.map((s) => (
        <button
          key={s}
          disabled={loading}
          onClick={() => onPick(s)}
          className="h-9 px-4 rounded-full bg-surface/90 backdrop-blur ring-1 ring-line text-xs text-dim hover:text-ink hover:ring-teal/50 transition-colors disabled:opacity-50"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
