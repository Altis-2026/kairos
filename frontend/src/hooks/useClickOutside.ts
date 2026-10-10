import { useEffect, type RefObject } from "react";

export function useClickOutside(
  ref: RefObject<HTMLElement | null>,
  onOutside: () => void,
  options: { enabled?: boolean; ignoreSelector?: string } = {}
) {
  const { enabled = true, ignoreSelector } = options;

  useEffect(() => {
    if (!enabled) return;
    const handler = (e: MouseEvent | TouchEvent) => {
      const el = ref.current;
      if (!el) return;
      const target = e.target as Node | null;
      if (target && el.contains(target)) return;

      if (ignoreSelector && target instanceof Element && target.closest(ignoreSelector)) {
        return;
      }
      onOutside();
    };
    document.addEventListener("mousedown", handler, true);
    document.addEventListener("touchstart", handler, true);
    return () => {
      document.removeEventListener("mousedown", handler, true);
      document.removeEventListener("touchstart", handler, true);
    };
  }, [enabled]);
}
