export interface PassEstimate {
  nextDate: string;
  daysAway: number;
  cadenceDays: number;
  lastDate: string;
}

const DAY_MS = 86400000;

function median(values: number[]): number {
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

// Estimates the next acquisition from the cadence Kairos actually observed in
// the archive for this footprint, rather than propagating the orbit. With one
// scene there is no cadence to measure, so it falls back to Sentinel-1's
// nominal 12-day repeat.
export function estimateNextPass(dates: string[]): PassEstimate | null {
  const times = dates
    .map((d) => Date.parse(d))
    .filter((t) => !Number.isNaN(t))
    .sort((a, b) => a - b);
  if (!times.length) return null;

  const gaps: number[] = [];
  for (let i = 1; i < times.length; i++) {
    const days = Math.round((times[i] - times[i - 1]) / DAY_MS);
    if (days > 0) gaps.push(days);
  }

  const cadence = gaps.length ? Math.max(1, Math.round(median(gaps))) : 12;
  const last = times[times.length - 1];

  let next = last + cadence * DAY_MS;
  const now = Date.now();
  while (next < now) next += cadence * DAY_MS;

  return {
    nextDate: new Date(next).toISOString().slice(0, 10),
    daysAway: Math.max(0, Math.ceil((next - now) / DAY_MS)),
    cadenceDays: cadence,
    lastDate: new Date(last).toISOString().slice(0, 10),
  };
}
