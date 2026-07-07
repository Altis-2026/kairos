export type Verdict = "flagged" | "natural" | "skip";

export interface Finding {
  id: string;
  zoneId: string;
  zoneName: string;
  country: string;
  analysisType: string;

  metricLabel: string;
  metricValue: number;
  metricUnit: string;
  dataDate: string;
  verdict: Verdict;
  note?: string;
  createdAt: number;
}

const KEY = "kairos_guardian_findings";

export function loadFindings(): Finding[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as Finding[]) : [];
  } catch {
    return [];
  }
}

export function saveFinding(f: Omit<Finding, "id" | "createdAt">): Finding[] {
  const finding: Finding = {
    ...f,
    id: `${f.zoneId}-${Date.now()}`,
    createdAt: Date.now(),
  };
  const next = [finding, ...loadFindings()].slice(0, 200);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {

  }
  return next;
}

export interface PatrolStats {
  reviewed: number;
  flagged: number;
  zones: number;
}

export function patrolStats(findings: Finding[]): PatrolStats {
  const reviewed = findings.filter((f) => f.verdict !== "skip").length;
  const flagged = findings.filter((f) => f.verdict === "flagged").length;
  const zones = new Set(findings.map((f) => f.zoneId)).size;
  return { reviewed, flagged, zones };
}
