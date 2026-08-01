import type { RiskOutlook } from "../api/foresight";
import { HAZARD_NAMES, PLAYBOOKS } from "./preparedness";

export interface ScanLine {
  label: string;
  sentence: string;
}

export interface ReportInput {
  placeName: string;
  scans?: ScanLine[];
  outlooks?: RiskOutlook[];
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const LEVEL_COLOR: Record<string, string> = {
  low: "#0F8A6E",
  moderate: "#B7791F",
  high: "#C05621",
  "very high": "#B3123B",
};

function outlookBlock(o: RiskOutlook): string {
  const name = HAZARD_NAMES[o.hazard] ?? o.hazard;
  const color = LEVEL_COLOR[o.level] ?? "#333";
  const peaks = o.seasonal.peak_months.length
    ? `<p class="meta">Peak months: ${escapeHtml(o.seasonal.peak_months.join(", "))}</p>`
    : "";
  const trend = o.trend
    ? `<p class="meta">Trend test: ${escapeHtml(o.trend.summary)}</p>`
    : "";
  const drivers = o.drivers
    .map((d) => `<li>${escapeHtml(d)}</li>`)
    .join("");
  const before = (PLAYBOOKS[o.hazard]?.before ?? [])
    .map((t) => `<li>${escapeHtml(t)}</li>`)
    .join("");

  return `
    <section class="hazard">
      <div class="hazard-head">
        <h3>${escapeHtml(name)}</h3>
        <span class="score" style="color:${color}">
          ${o.score}<span class="score-max">/100</span>
          <em>${escapeHtml(o.level)}</em>
        </span>
      </div>
      <ul class="drivers">${drivers}</ul>
      ${peaks}
      ${trend}
      <p class="meta small">Record used: ${escapeHtml(o.data_years)}</p>
      ${before ? `<h4>Before it happens</h4><ul class="todo">${before}</ul>` : ""}
      <p class="method">${escapeHtml(o.method)}</p>
    </section>`;
}

export function buildPlaceReport(input: ReportInput): string {
  const now = new Date().toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const scanRows = (input.scans ?? [])
    .map(
      (s) => `
        <tr>
          <th>${escapeHtml(s.label)}</th>
          <td>${escapeHtml(s.sentence)}</td>
        </tr>`
    )
    .join("");

  const outlooks = (input.outlooks ?? []).map(outlookBlock).join("");

  const highest = (input.outlooks ?? [])
    .slice()
    .sort((a, b) => b.score - a.score)[0];

  const headline = highest
    ? `The biggest measured exposure here is ${(
        HAZARD_NAMES[highest.hazard] ?? highest.hazard
      ).toLowerCase()}, scoring ${highest.score} out of 100 (${highest.level}).`
    : "";

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Kairos report: ${escapeHtml(input.placeName)}</title>
<style>
  @page { margin: 18mm; }
  * { box-sizing: border-box; }
  body {
    font: 13px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #14201a; margin: 0; padding: 28px; max-width: 760px;
  }
  header { border-bottom: 2px solid #0F8A6E; padding-bottom: 12px; margin-bottom: 20px; }
  .brand { font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: #0F8A6E; }
  h1 { font-size: 21px; margin: 6px 0 4px; }
  .sub { color: #5b6b60; font-size: 12px; margin: 0; }
  .headline {
    background: #f2f8f5; border-left: 3px solid #0F8A6E; padding: 10px 12px;
    margin: 0 0 20px; font-size: 13.5px;
  }
  h2 { font-size: 14px; text-transform: uppercase; letter-spacing: 0.1em;
       color: #5b6b60; margin: 24px 0 10px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; vertical-align: top; padding: 8px 10px;
           border-bottom: 1px solid #e2e9e4; }
  th { width: 34%; font-weight: 600; }
  .hazard { border: 1px solid #e2e9e4; border-radius: 8px; padding: 14px 16px;
            margin-bottom: 14px; page-break-inside: avoid; }
  .hazard-head { display: flex; justify-content: space-between; align-items: baseline; }
  .hazard h3 { margin: 0; font-size: 15px; }
  .score { font-size: 22px; font-weight: 700; }
  .score-max { font-size: 12px; font-weight: 400; color: #8a9e8c; }
  .score em { display: block; font-size: 10px; font-style: normal;
              text-transform: uppercase; letter-spacing: 0.12em; text-align: right; }
  .hazard h4 { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em;
               color: #5b6b60; margin: 12px 0 6px; }
  ul { margin: 8px 0; padding-left: 18px; }
  li { margin-bottom: 4px; }
  .meta { color: #3d4f45; margin: 6px 0; }
  .small { font-size: 11px; color: #7b8a80; }
  .method { font-size: 11px; color: #7b8a80; margin: 10px 0 0;
            border-top: 1px solid #eef3f0; padding-top: 8px; }
  footer { margin-top: 26px; border-top: 1px solid #e2e9e4; padding-top: 12px;
           font-size: 11px; color: #7b8a80; }
  @media print { body { padding: 0; } }
</style>
</head>
<body>
<header>
  <div class="brand">Kairos satellite report</div>
  <h1>${escapeHtml(input.placeName)}</h1>
  <p class="sub">Prepared ${escapeHtml(now)} from public satellite records</p>
</header>

${headline ? `<p class="headline">${escapeHtml(headline)}</p>` : ""}

${
  scanRows
    ? `<h2>What the satellites see right now</h2><table>${scanRows}</table>`
    : ""
}

${outlooks ? `<h2>Long-term exposure</h2>${outlooks}` : ""}

<footer>
  Built with Kairos, which reads free Sentinel-1 radar and other public
  satellite archives. Every figure here is computed from measured history,
  not a forecast of a specific future event. Radar has known false positives,
  so treat this as a well-sourced starting point rather than a survey.
  Data: ESA Copernicus Sentinel-1, EC JRC Global Surface Water, NASA MODIS,
  UCSB CHIRPS, ESA WorldCover.
</footer>
</body>
</html>`;
}

export function openPlaceReport(input: ReportInput) {
  const html = buildPlaceReport(input);
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
