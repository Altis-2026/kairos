import { useEffect, useState } from "react";

/** Matches Tailwind's `lg` breakpoint (1024px) — the same cutoff panelShell
 * uses. Below it: phones and portrait tablets, where floating side-by-side
 * chrome has nowhere to go without overlapping. At or above it: tablets in
 * landscape and desktops, where the original floating layout has room. */
const QUERY = "(max-width: 1023px)";

export function useIsCompact(): boolean {
  const [compact, setCompact] = useState(
    () => typeof window !== "undefined" && window.matchMedia(QUERY).matches
  );

  useEffect(() => {
    const mql = window.matchMedia(QUERY);
    const onChange = () => setCompact(mql.matches);
    onChange();
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return compact;
}
