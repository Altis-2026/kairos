const SEEN_KEY = "kairos_notified_findings";
const ENABLED_KEY = "kairos_notify_enabled";
const MAX_REMEMBERED = 200;

export function notificationsSupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

export function notificationsEnabled(): boolean {
  if (!notificationsSupported() || Notification.permission !== "granted") {
    return false;
  }
  try {
    return localStorage.getItem(ENABLED_KEY) === "1";
  } catch {
    return false;
  }
}

export async function enableNotifications(): Promise<boolean> {
  if (!notificationsSupported()) return false;
  let permission = Notification.permission;
  if (permission === "default") {
    permission = await Notification.requestPermission();
  }
  if (permission !== "granted") return false;
  try {
    localStorage.setItem(ENABLED_KEY, "1");
  } catch {
    return true;
  }
  return true;
}

export function disableNotifications() {
  try {
    localStorage.setItem(ENABLED_KEY, "0");
  } catch {
    return;
  }
}

function readSeen(): number[] {
  try {
    const raw = localStorage.getItem(SEEN_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((n) => typeof n === "number") : [];
  } catch {
    return [];
  }
}

function writeSeen(ids: number[]) {
  try {
    localStorage.setItem(SEEN_KEY, JSON.stringify(ids.slice(0, MAX_REMEMBERED)));
  } catch {
    return;
  }
}

export interface NotifiableFinding {
  id: number;
  region: string;
  display_name: string;
  headline_label?: string | null;
  headline_value?: number | null;
  headline_unit?: string | null;
}

// First visit records what already exists without firing a burst of alerts for
// history the user never asked about.
export function syncFindingNotifications(findings: NotifiableFinding[]): number {
  if (!findings.length) return 0;
  const seen = readSeen();
  const known = new Set(seen);
  const fresh = findings.filter((f) => !known.has(f.id));
  const allIds = [...findings.map((f) => f.id), ...seen];
  const deduped = Array.from(new Set(allIds));

  if (!seen.length) {
    writeSeen(deduped);
    return 0;
  }
  writeSeen(deduped);

  if (!notificationsEnabled()) return 0;

  for (const f of fresh.slice(0, 3)) {
    const stat =
      f.headline_value != null && f.headline_label
        ? `${f.headline_label}: ${Math.round(f.headline_value).toLocaleString()} ${
            f.headline_unit ?? ""
          }`.trim()
        : f.display_name;
    try {
      new Notification(`Kairos found something in ${f.region}`, {
        body: stat,
        icon: "/icons/icon-192.png",
        tag: `kairos-finding-${f.id}`,
      });
    } catch {
      break;
    }
  }
  return fresh.length;
}
