export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export function apiConfigProblem(): string | null {
  const onLocalhost =
    location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if (!onLocalhost && API_BASE.includes("localhost")) {
    return (
      "This deployment does not know the backend's address. Set the " +
      "VITE_API_BASE_URL environment variable in Vercel to the backend's " +
      "public URL and redeploy the frontend."
    );
  }
  return null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    const config = apiConfigProblem();
    throw new ApiError(
      0,
      config ??
        "Could not reach the Kairos backend. It may be waking up from idle; " +
          "wait a few seconds and try again."
    );
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail) detail = JSON.stringify(body.detail);
    } catch {

    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}
