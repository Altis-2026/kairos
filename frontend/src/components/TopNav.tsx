/**
 * Top navigation: Altis brand (left), menu + location search (center),
 * help + sign-in (right). Cmd/Ctrl+K focuses the search.
 */
import { useEffect, useRef, useState } from "react";
import { HelpCircle, Menu, Search, LogOut } from "lucide-react";
import { useMapStore } from "../stores/mapStore";
import { useSidebarStore } from "../stores/sidebarStore";
import { useAuthStore } from "../stores/authStore";
import { firebaseEnabled, signInWithGoogle, signOut } from "../lib/firebase";

const MAPBOX_TOKEN = (import.meta.env.VITE_MAPBOX_TOKEN as string) || "";

export default function TopNav() {
  const [search, setSearch] = useState("");
  const [searching, setSearching] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const requestFlyTo = useMapStore((s) => s.requestFlyTo);
  const toggleSidebar = useSidebarStore((s) => s.toggleSidebar);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function geocode() {
    const q = search.trim();
    if (!q || !MAPBOX_TOKEN) return;
    setSearching(true);
    try {
      const res = await fetch(
        `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(
          q
        )}.json?access_token=${MAPBOX_TOKEN}&limit=1`
      );
      const data = await res.json();
      const feature = data.features?.[0];
      if (feature?.center) {
        const zoom = feature.bbox ? 6 : 9;
        requestFlyTo([feature.center[0], feature.center[1]], zoom);
      }
    } finally {
      setSearching(false);
    }
  }

  async function handleSignIn() {
    setAuthError(null);
    try {
      await signInWithGoogle();
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : "Sign-in failed.");
    }
  }

  return (
    <header className="absolute top-0 inset-x-0 z-30 flex items-center gap-4 px-5 h-16 pointer-events-none">
      {/* Brand */}
      <div className="flex items-center gap-3 pointer-events-auto">
        <img
          src="/altis-logo.png"
          alt="Altis"
          className="h-9 w-9 rounded-xl ring-1 ring-line"
        />
        <div className="leading-tight">
          <div className="font-display font-semibold text-lg text-ink tracking-tight">
            Altis
          </div>
          <div className="font-mono text-[9px] tracking-[0.22em] text-dim">
            KAIROS · SAR PLATFORM
          </div>
        </div>
      </div>

      {/* Menu + Search */}
      <div className="flex-1 flex items-center justify-center gap-3 pointer-events-auto">
        <button
          onClick={toggleSidebar}
          className="flex items-center gap-2 h-10 px-4 rounded-full bg-surface/90 backdrop-blur ring-1 ring-line text-sm text-ink hover:ring-amber/60 transition-colors"
        >
          <Menu size={16} className="text-dim" />
          Menu
        </button>
        <div className="relative w-full max-w-md">
          <Search
            size={15}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-dim"
          />
          <input
            ref={inputRef}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && geocode()}
            placeholder="Search locations…"
            className="w-full h-10 pl-10 pr-14 rounded-full bg-surface/90 backdrop-blur ring-1 ring-line text-sm text-ink placeholder-dim outline-none focus:ring-amber/60 transition-shadow"
          />
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 font-mono text-[10px] text-dim bg-raised px-1.5 py-0.5 rounded ring-1 ring-line">
            {searching ? "…" : "⌘K"}
          </kbd>
        </div>
      </div>

      {/* Help + Auth */}
      <div className="flex items-center gap-3 pointer-events-auto">
        <a
          href="https://docs.kairos.earth"
          target="_blank"
          rel="noreferrer"
          title="Help"
          className="h-10 w-10 grid place-items-center rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-ink transition-colors"
        >
          <HelpCircle size={17} />
        </a>
        {user ? (
          <div className="flex items-center gap-2">
            {user.photoUrl ? (
              <img
                src={user.photoUrl}
                alt={user.name ?? "Account"}
                title={user.email ?? undefined}
                className="h-10 w-10 rounded-full ring-1 ring-teal/60 object-cover"
              />
            ) : (
              <div className="h-10 w-10 grid place-items-center rounded-full bg-raised ring-1 ring-teal/60 font-display text-teal">
                {(user.name ?? "U").slice(0, 1)}
              </div>
            )}
            <button
              onClick={() => signOut()}
              title="Sign out"
              className="h-10 w-10 grid place-items-center rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-ink transition-colors"
            >
              <LogOut size={15} />
            </button>
          </div>
        ) : (
          <button
            onClick={handleSignIn}
            title={
              firebaseEnabled
                ? "Sign in with Google"
                : "Add Firebase config to frontend/.env to enable sign-in"
            }
            className="h-10 px-4 rounded-full bg-amber text-bg font-medium text-sm hover:brightness-110 transition disabled:opacity-60"
          >
            Sign in
          </button>
        )}
      </div>

      {authError && (
        <div className="absolute top-16 right-5 max-w-xs bg-surface ring-1 ring-line rounded-xl p-3 text-xs text-dim pointer-events-auto shadow-panel">
          {authError}
        </div>
      )}
    </header>
  );
}
