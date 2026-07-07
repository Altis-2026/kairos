import { useChatStore } from "../../stores/chatStore";

const SUGGESTIONS = [
  "Flooding in Bangladesh, August 2024",
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
    <div className="w-full max-w-2xl flex gap-2 pointer-events-auto overflow-x-auto pb-1 sm:flex-wrap sm:justify-center sm:overflow-visible sm:pb-0">
      {SUGGESTIONS.map((s) => (
        <button
          key={s}
          disabled={loading}
          onClick={() => onPick(s)}
          className="h-9 px-4 shrink-0 whitespace-nowrap rounded-full bg-surface/90 backdrop-blur ring-1 ring-line text-xs text-dim hover:text-ink hover:ring-teal/50 transition-colors disabled:opacity-50"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
