/**
 * Shared responsive shell for Kairos's floating panels.
 *
 * Below `lg` (1024px — phones and portrait tablets), a floating side panel
 * has nowhere safe to float: there isn't room for it beside the toolbars and
 * the chat bar without overlapping something. So every panel collapses to
 * the SAME bounded sheet (inset-x-3, top-24, bottom-3) below `lg`, which is
 * guaranteed clear of the top nav and the chat bar. At `lg` and up, the
 * `desktop` classes take over and reproduce the original floating panel
 * geometry exactly — desktop layout is unchanged.
 *
 * IMPORTANT — why the mobile geometry is scoped under `max-lg:` and not reset
 * with `lg:*-auto`:
 *   Tailwind emits utilities in a fixed source order, and between two
 *   equal-specificity `lg:` utilities the one printed LATER wins regardless of
 *   attribute order. `lg:top-auto` happens to be emitted after `lg:top-1/2`,
 *   so a naive "reset then re-position" (`lg:top-auto ... lg:top-1/2`) leaves
 *   the panel at `top: auto` on desktop — which drops it to its static
 *   position at the bottom of the document, off-screen. Scoping the mobile
 *   geometry under `max-lg:` means those utilities simply do not exist at
 *   `lg`+, so the desktop classes own positioning outright with nothing to
 *   override and no cascade race to lose.
 *
 * Two variants:
 *   panelShell()      for panels with plain content (no internal flex/scroll
 *                      management) — adds overflow-y-auto on the mobile sheet.
 *   panelShellFlex()   for panels that already manage their own header +
 *                      scrollable content region (flex flex-col + an inner
 *                      flex-1 overflow-y-auto) — leaves overflow alone so the
 *                      inner region keeps doing the scrolling.
 *
 * Each panel's `desktop` string MUST fully anchor the panel at `lg`+ (a
 * horizontal edge, a width, and a vertical anchor — a `top`, a `top`+`bottom`
 * pair, or a `bottom` with content-driven height).
 */

// Look shared at every size — everything except position.
const PANEL_CHROME =
  "absolute z-40 rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4";

// Bounded mobile sheet, applied ONLY below `lg` so it never fights the
// desktop position classes in the cascade.
const MOBILE_GEOMETRY = "max-lg:inset-x-3 max-lg:top-24 max-lg:bottom-3";

export function panelShell(desktop: string): string {
  return `${PANEL_CHROME} ${MOBILE_GEOMETRY} max-lg:overflow-y-auto ${desktop}`;
}

export function panelShellFlex(desktop: string): string {
  return `${PANEL_CHROME} ${MOBILE_GEOMETRY} flex flex-col ${desktop}`;
}
