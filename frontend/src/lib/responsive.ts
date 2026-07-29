// Below lg (1024px) every floating panel collapses to the same bounded sheet
// that clears the top nav and the chat bar. The mobile geometry is scoped
// under max-lg: instead of being reset with lg:*-auto because Tailwind emits
// utilities in fixed source order: between two equal-specificity lg:
// utilities the one printed later wins, and lg:top-auto happens to print
// after lg:top-1/2, which would leave the panel at top:auto on desktop.

const PANEL_CHROME =
  "absolute z-40 rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4";

const MOBILE_GEOMETRY = "max-lg:inset-x-3 max-lg:top-24 max-lg:bottom-3";

export function panelShell(desktop: string): string {
  return `${PANEL_CHROME} ${MOBILE_GEOMETRY} max-lg:overflow-y-auto ${desktop}`;
}

export function panelShellFlex(desktop: string): string {
  return `${PANEL_CHROME} ${MOBILE_GEOMETRY} flex flex-col ${desktop}`;
}
