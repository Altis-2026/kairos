const PANEL_CHROME =
  "absolute z-40 rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4";

const MOBILE_GEOMETRY = "max-lg:inset-x-3 max-lg:top-24 max-lg:bottom-3";

export function panelShell(desktop: string): string {
  return `${PANEL_CHROME} ${MOBILE_GEOMETRY} max-lg:overflow-y-auto ${desktop}`;
}

export function panelShellFlex(desktop: string): string {
  return `${PANEL_CHROME} ${MOBILE_GEOMETRY} flex flex-col ${desktop}`;
}
