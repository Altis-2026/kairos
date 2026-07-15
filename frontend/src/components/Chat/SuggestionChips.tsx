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
    <div className="w-full max-w-full overflow-x-auto pointer-events-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className="flex justify-center sm:flex-wrap gap-2 px-1 w-max sm:w-full mx-auto">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            disabled={loading}
            onClick={() => onPick(s)}
            className="h-9 px-4 rounded-full bg-surface/90 backdrop-blur ring-1 ring-line text-xs text-dim hover:text-ink hover:ring-teal/50 transition-colors disabled:opacity-50 whitespace-nowrap shrink-0"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
