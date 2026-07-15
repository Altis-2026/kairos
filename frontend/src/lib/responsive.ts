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
 * Two variants:
 *   panelShell()      for panels with plain content (no internal flex/scroll
 *                      management) — adds overflow-y-auto on the mobile sheet.
 *   panelShellFlex()   for panels that already manage their own header +
 *                      scrollable content region (flex flex-col + an inner
 *                      flex-1 overflow-y-auto) — leaves overflow alone so the
 *                      inner region keeps doing the scrolling.
 */

const MOBILE_BASE =
  "absolute inset-x-3 top-24 bottom-3 z-40 rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4";

export function panelShell(desktop: string): string {
  return `${MOBILE_BASE} overflow-y-auto lg:overflow-visible lg:inset-x-auto lg:top-auto lg:bottom-auto ${desktop}`;
}

export function panelShellFlex(desktop: string): string {
  return `${MOBILE_BASE} flex flex-col lg:inset-x-auto lg:top-auto lg:bottom-auto ${desktop}`;
}
