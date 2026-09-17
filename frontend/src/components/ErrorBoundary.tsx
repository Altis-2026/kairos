/**
 * Contains a crash to the one panel that threw it.
 *
 * React has exactly one way to survive a render-time exception: a class
 * component implementing `getDerivedStateFromError`. Without one anywhere in
 * the tree, an uncaught error unmounts the entire app — every button on the
 * page stops responding, not just the panel that broke, because the whole
 * React root is gone. That is a real failure this app hit: `JanusPanel` once
 * read a field the backend didn't send, and the single missing key took the
 * whole UI down with it (see the entitlements fix in janus/entitlements.py).
 *
 * That specific bug is now fixed at its source, and the panel that read the
 * field defensively guards it too. This boundary is the layer underneath
 * both of those: whatever the next bug turns out to be, in this panel or a
 * different one, it should cost the user one broken panel and a click to
 * dismiss it — never the whole app.
 *
 * Deliberately NOT wired to retry in place. Every panel this wraps is
 * conditionally rendered by its parent (`{openPanel === "x" && <Boundary>…}`),
 * so closing and reopening already mounts a fresh instance with a clean
 * error state — there is no "try again" the boundary needs to own, only a
 * way to get back to a screen that responds to clicks.
 */
import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { panelShell } from "../lib/responsive";

interface Props {
  children: ReactNode;
  /** What to call so the parent stops rendering this panel — its own close. */
  onDismiss: () => void;
  /** Shown in the fallback card, e.g. "Janus". */
  label: string;
}

interface State {
  error: Error | null;
}

export default class PanelErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error(`[${this.props.label} panel crashed]`, error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <aside className={panelShell("lg:right-20 lg:left-auto lg:top-1/2 lg:-translate-y-1/2 lg:w-96")}>
        <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-amber">
          <AlertTriangle size={13} />
          {this.props.label.toUpperCase()} HIT A PROBLEM
        </div>
        <p className="mt-3 text-xs leading-relaxed text-dim">
          Something in this panel broke. The rest of Kairos is unaffected —
          closing this and opening it again usually clears it.
        </p>
        <button
          onClick={this.props.onDismiss}
          className="mt-4 w-full h-9 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition"
        >
          Close {this.props.label}
        </button>
      </aside>
    );
  }
}

/**
 * Last resort for the whole app, not just one panel.
 *
 * `PanelErrorBoundary` above assumes there is a working app underneath to
 * fall back to — that's true for anything RightToolbar renders, but not for
 * a crash in something structural (the globe, the top nav, the sidebar
 * wizard). Wrapping the app's own render root in this means even that
 * produces a small "something broke, reload" screen instead of a blank,
 * frozen tab with no indication anything happened at all.
 */
export class AppErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("[Kairos crashed]", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="fixed inset-0 z-[999] grid place-items-center bg-bg px-5">
        <div className="max-w-sm text-center space-y-4">
          <div className="mx-auto h-12 w-12 grid place-items-center rounded-2xl bg-raised ring-1 ring-amber/30 text-amber">
            <AlertTriangle size={22} />
          </div>
          <h1 className="font-display text-lg text-ink">
            Kairos hit a problem
          </h1>
          <p className="text-sm text-dim leading-relaxed">
            Something went wrong loading the app. Reloading almost always
            clears it — nothing you were doing caused this.
          </p>
          <button
            onClick={() => location.reload()}
            className="w-full h-10 rounded-xl bg-amber text-bg font-medium text-sm hover:brightness-110 transition"
          >
            Reload Kairos
          </button>
        </div>
      </div>
    );
  }
}
