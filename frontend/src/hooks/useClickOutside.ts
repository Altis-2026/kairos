/**
 * Close a floating panel when the user clicks (or taps) anywhere outside it.
 *
 * None of Kairos's side panels are modal dialogs — they're plain siblings
 * positioned over the map, so nothing in the DOM tree stops a click from
 * reaching the globe or the other toolbars underneath. That's deliberate:
 * the point is to let someone open Janus, see it's locked, and go do
 * something else without hunting for the panel's own X first. This hook is
 * what makes "somewhere else" actually dismiss the panel instead of the
 * panel just sitting there until its own close button is found.
 *
 * `mousedown` rather than `click`, and capture phase, so this fires and the
 * state update commits before whatever was actually clicked handles its own
 * event — including another toolbar button, which should both close this
 * panel and open the one just clicked, not fight over which wins.
 */
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
      // The button that opens this panel is, from the panel's own point of
      // view, "outside" it — so without this, closing it the normal way (a
      // second click on the same toolbar icon) fired this handler first,
      // closed the panel, and then the button's own onClick read the
      // now-stale `openPanel` state as "closed" and reopened it. One click
      // that should close ended up doing nothing at all.
      if (
        ignoreSelector &&
        target instanceof Element &&
        target.closest(ignoreSelector)
      ) {
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);
}
