export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export interface ApiOptions extends RequestInit {
  timeoutMs?: number;
}

const SLOW_PATHS: [RegExp, number][] = [
  [/^\/simulate/, 280_000],
  [/^\/janus\/.*\/(chat|review|pack|notebook)/, 200_000],
  [
    /^\/(query|agent|analyze|featured|research|foresight|myplace|validation|confounders|vessels|impact|export)/,
    180_000,
  ],
];

function defaultTimeout(path: string): number {
  for (const [pattern, ms] of SLOW_PATHS) if (pattern.test(path)) return ms;
  return 30_000;
}

function linkSignals(outer: AbortSignal | null | undefined, inner: AbortController) {
  if (!outer) return;
  if (outer.aborted) inner.abort(outer.reason);
  else outer.addEventListener("abort", () => inner.abort(outer.reason), { once: true });
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { timeoutMs = defaultTimeout(path), signal, headers, ...rest } = options;
  const controller = new AbortController();
  linkSignals(signal, controller);
  const timer = setTimeout(() => controller.abort("timeout"), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: { "Content-Type": "application/json", ...headers },
      signal: controller.signal,
    });
  } catch {
    if (controller.signal.aborted) {
      if (controller.signal.reason === "timeout") {
        throw new ApiError(
          408,
          "That took longer than expected. Earth Engine may be busy, so try a smaller area or try again in a minute."
        );
      }
      throw new ApiError(499, "Cancelled.");
    }
    throw new ApiError(
      0,
      navigator.onLine
        ? "Kairos couldn't reach its server. It may be waking up, so try again in a few seconds."
        : "You're offline. Reconnect and try again."
    );
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) detail = body.detail[0].msg;
      else if (body.detail) detail = JSON.stringify(body.detail);
    } catch {
      detail = res.status >= 500 ? "The server hit an error. Try again in a moment." : detail;
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export function isCancelled(e: unknown): boolean {
  return e instanceof ApiError && e.status === 499;
}
