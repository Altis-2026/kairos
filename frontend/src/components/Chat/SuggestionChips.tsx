import { useChatStore } from "../../stores/chatStore";
import { useT, type StringKey } from "../../lib/i18n";

const STARTERS: StringKey[] = ["suggestion1", "suggestion2", "suggestion3", "suggestion4"];
const FOLLOW_UPS: StringKey[] = ["followCompare", "followDamage", "followWorse"];

export default function SuggestionChips({ onPick }: { onPick: (text: string) => void }) {
  const t = useT();
  const loading = useChatStore((s) => s.loading);
  const messages = useChatStore((s) => s.messages);
  const panelOpen = useChatStore((s) => s.panelOpen);

  const last = messages[messages.length - 1];
  const lastHadResult = !!last?.results?.length && last.results[0].mode !== "simulated";
  const keys = messages.length === 0 ? STARTERS : lastHadResult && panelOpen ? FOLLOW_UPS : [];
  if (!keys.length) return null;

  return (
    <div className="w-full max-w-full overflow-x-auto pointer-events-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className="flex justify-center sm:flex-wrap gap-2 px-1 w-max sm:w-full mx-auto">
        {keys.map((k) => (
          <button
            key={k}
            disabled={loading}
            onClick={() => onPick(t(k))}
            className="h-9 px-4 rounded-full bg-surface/90 backdrop-blur ring-1 ring-line text-xs text-dim hover:text-ink hover:ring-teal/50 transition-colors disabled:opacity-50 whitespace-nowrap shrink-0"
          >
            {t(k)}
          </button>
        ))}
      </div>
    </div>
  );
}
