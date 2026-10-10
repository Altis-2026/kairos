import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { panelShell } from "../lib/responsive";

interface Props {
  children: ReactNode;

  onDismiss: () => void;

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
          Something in this panel broke. The rest of Kairos is unaffected, and closing it and opening it again
          usually clears it.
        </p>
        <button
          onClick={() => {
            this.setState({ error: null });
            this.props.onDismiss();
          }}
          className="mt-4 w-full h-9 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition"
        >
          Close {this.props.label}
        </button>
      </aside>
    );
  }
}

export class AppErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
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
          <h1 className="font-display text-lg text-ink">Kairos hit a problem</h1>
          <p className="text-sm text-dim leading-relaxed">
            Something went wrong loading the app. Reloading almost always clears it. Nothing you were doing
            caused this.
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
