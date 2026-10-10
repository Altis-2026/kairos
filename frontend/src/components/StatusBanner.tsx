import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, X } from "lucide-react";
import { API_BASE } from "../api/client";

type State = "checking" | "ok" | "waking" | "down" | "misconfigured";

function misconfigured(): boolean {
  const local = ["localhost", "127.0.0.1"].includes(location.hostname);
  return !local && API_BASE.includes("localhost");
}

async function ping(timeoutMs: number): Promise<boolean> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: controller.signal });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

export default function StatusBanner() {
  const [state, setState] = useState<State>(misconfigured() ? "misconfigured" : "checking");
  const [dismissed, setDismissed] = useState(false);

  async function check() {
    if (misconfigured()) return;
    setState("checking");
    if (await ping(6000)) return setState("ok");
    setState("waking");
    for (let i = 0; i < 4; i++) {
      await new Promise((r) => setTimeout(r, 4000));
      if (await ping(8000)) return setState("ok");
    }
    setState("down");
  }

  useEffect(() => {
    void check();
  }, []);

  if (dismissed || state === "ok" || state === "checking") return null;

  const message = {
    misconfigured:
      "This deployment doesn't know where the Kairos server is. Set VITE_API_BASE_URL to the backend URL and redeploy.",
    waking: "Kairos's server is waking up. This takes a few seconds the first time.",
    down: "Kairos can't reach its server right now. The map still works, and analyses will run once it's back.",
  }[state];

  return (
    <div
      role="status"
      className="absolute top-[4.5rem] inset-x-3 sm:inset-x-auto sm:left-1/2 sm:-translate-x-1/2 sm:max-w-lg z-40 rounded-xl bg-surface/95 backdrop-blur ring-1 ring-amber/50 shadow-panel p-3 flex items-start gap-2.5"
    >
      {state === "waking" ? (
        <RefreshCw size={15} className="text-amber shrink-0 mt-0.5 animate-spin" />
      ) : (
        <AlertTriangle size={15} className="text-amber shrink-0 mt-0.5" />
      )}
      <p className="flex-1 text-xs text-dim leading-relaxed">{message}</p>
      {state === "down" && (
        <button onClick={() => void check()} className="text-xs text-teal hover:underline shrink-0">
          Retry
        </button>
      )}
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
        className="text-dim hover:text-ink shrink-0"
      >
        <X size={14} />
      </button>
    </div>
  );
}
