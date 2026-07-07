import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Bell, BellRing, Loader2, Radar, Trash2, X } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { useAlertsStore, type SavedAlert } from "../../stores/alertsStore";
import {
  alertsAvailable,
  deleteAlert,
  loadAlerts,
  markAlertChecked,
} from "../../lib/alerts";
import { checkAlert } from "../../api/alerts";
import { applyResultToGlobe } from "../../lib/applyResult";

export default function AlertsPanel({ onClose }: { onClose: () => void }) {
  const user = useAuthStore((s) => s.user);
  const { alerts, loading, error } = useAlertsStore();
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [flash, setFlash] = useState<Record<string, string>>({});

  useEffect(() => {
    if (user) loadAlerts();
  }, [user]);

  function setFlashFor(id: string, msg: string) {
    setFlash((f) => ({ ...f, [id]: msg }));
    setTimeout(
      () =>
        setFlash((f) => {
          const next = { ...f };
          delete next[id];
          return next;
        }),
      6000
    );
  }

  async function check(a: SavedAlert) {
    setCheckingId(a.id);
    try {
      const res = await checkAlert({
        analysis_type: a.analysisType,
        bbox: a.bbox,
        since_date: a.lastDataDate,
      });
      if (res.new && res.result) {
        applyResultToGlobe(res.result);
        await markAlertChecked(a.id, {
          lastDataDate: res.result.data_date,
          lastHeadlineValue: res.result.headline_stat.value,
          lastHeadlineUnit: res.result.headline_stat.unit,
        });
        setFlashFor(a.id, `New pass ${res.result.data_date}, result on globe.`);
        onClose();
      } else if (res.data_date) {
        await markAlertChecked(a.id, {});
        setFlashFor(a.id, `No new pass since ${res.data_date}.`);
      } else {
        setFlashFor(a.id, res.note ?? "No new Sentinel-1 pass yet.");
      }
    } catch (e) {
      setFlashFor(a.id, e instanceof Error ? e.message : "Check failed.");
    } finally {
      setCheckingId(null);
    }
  }

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[58dvh] sm:right-20 sm:top-1/2 sm:-translate-y-1/2 sm:w-80 sm:max-h-[82vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-dim">
          <Bell size={12} /> ALERTS
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      {!alertsAvailable() ? (
        <p className="text-xs text-dim leading-relaxed">
          Alerts need Firebase configured. Add the{" "}
          <span className="font-mono text-teal">VITE_FIREBASE_*</span> values to
          enable watching areas.
        </p>
      ) : !user ? (
        <p className="text-xs text-dim leading-relaxed">
          Sign in to watch an area. Run an analysis, then use{" "}
          <span className="text-teal">Watch this area</span> in the research panel
          to start an alert.
        </p>
      ) : loading ? (
        <div className="flex items-center gap-2 text-xs text-dim">
          <Loader2 size={14} className="animate-spin" /> Loading alerts…
        </div>
      ) : error ? (
        <p className="text-[11px] text-amber leading-relaxed">{error}</p>
      ) : alerts.length === 0 ? (
        <p className="text-xs text-dim leading-relaxed">
          No alerts yet. Run an analysis, then choose{" "}
          <span className="text-teal">Watch this area</span> to be able to re-check
          it for new Sentinel-1 passes.
        </p>
      ) : (
        <ul className="space-y-2 max-h-[26rem] overflow-y-auto">
          {alerts.map((a) => (
            <li
              key={a.id}
              className="rounded-xl bg-bg/70 ring-1 ring-line p-3 space-y-2"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-xs text-ink truncate">{a.label}</div>
                  <div className="font-mono text-[10px] text-dim mt-0.5">
                    {a.displayName}
                  </div>
                  <div className="font-mono text-[10px] text-dim/80 mt-0.5">
                    {a.lastDataDate
                      ? `last seen ${a.lastDataDate}`
                      : "not checked yet"}
                    {a.lastHeadlineValue != null &&
                      ` · ${a.lastHeadlineValue.toLocaleString()} ${a.lastHeadlineUnit ?? ""}`}
                  </div>
                </div>
                <button
                  onClick={() => deleteAlert(a.id)}
                  className="h-7 w-7 grid place-items-center rounded-lg ring-1 ring-line text-dim hover:text-ink transition shrink-0"
                  title="Delete alert"
                >
                  <Trash2 size={12} />
                </button>
              </div>
              <button
                onClick={() => check(a)}
                disabled={checkingId === a.id}
                className="w-full h-8 rounded-lg text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-teal hover:ring-teal/40 transition disabled:opacity-50"
                title="Check for a new Sentinel-1 pass now"
              >
                {checkingId === a.id ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Radar size={12} />
                )}
                Check now
              </button>
              {flash[a.id] && (
                <p className="flex items-start gap-1 text-[10px] text-teal leading-snug">
                  <BellRing size={11} className="mt-0.5 shrink-0" />
                  {flash[a.id]}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </motion.aside>
  );
}
