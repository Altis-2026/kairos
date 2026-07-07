import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import {
  HelpCircle,
  Menu,
  MoreVertical,
  Search,
  LogOut,
  MapPin,
  Radio,
  Shield,
} from "lucide-react";
import { useMapStore } from "../stores/mapStore";
import { useSidebarStore } from "../stores/sidebarStore";
import { useAuthStore } from "../stores/authStore";
import { firebaseEnabled, signInWithGoogle, signOut } from "../lib/firebase";

const MAPBOX_TOKEN = (import.meta.env.VITE_MAPBOX_TOKEN as string) || "";

interface Suggestion {
  id: string;
  name: string;
  center: [number, number];
  hasBbox: boolean;
}

export default function TopNav() {
  const [search, setSearch] = useState("");
  const [searching, setSearching] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [authError, setAuthError] = useState<string | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const justPickedRef = useRef(false);
  const requestFlyTo = useMapStore((s) => s.requestFlyTo);
  const setTutorialOpen = useMapStore((s) => s.setTutorialOpen);
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

  useEffect(() => {
    if (justPickedRef.current) {
      justPickedRef.current = false;
      return;
    }
    const q = search.trim();
    if (!q || !MAPBOX_TOKEN) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    setSearching(true);
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(
          `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(
            q
          )}.json?access_token=${MAPBOX_TOKEN}&limit=5&autocomplete=true`,
          { signal: controller.signal }
        );
        const data = await res.json();
        const next: Suggestion[] = (data.features ?? [])
          .filter((f: any) => Array.isArray(f.center))
          .map((f: any) => ({
            id: f.id,
            name: f.place_name as string,
            center: [f.center[0], f.center[1]] as [number, number],
            hasBbox: Array.isArray(f.bbox),
          }));
        setSuggestions(next);
        setActiveIndex(-1);
        setOpen(next.length > 0);
      } catch {

      } finally {
        setSearching(false);
      }
    }, 300);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [search]);

  function pick(s: Suggestion) {
    justPickedRef.current = true;
    setSearch(s.name);
    setOpen(false);
    setSuggestions([]);
    setActiveIndex(-1);
    requestFlyTo(s.center, s.hasBbox ? 7 : 10);
    inputRef.current?.blur();
  }

  function onSearchKeyDown(e: ReactKeyboardEvent<HTMLInputElement>) {
    if (!open || suggestions.length === 0) {
      if (e.key === "Enter" && suggestions[0]) pick(suggestions[0]);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      pick(suggestions[activeIndex >= 0 ? activeIndex : 0]);
    } else if (e.key === "Escape") {
      setOpen(false);
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
    <header className="absolute top-0 inset-x-0 z-30 flex items-center gap-2 sm:gap-4 px-3 sm:px-5 h-16 pointer-events-none">
      <div className="flex items-center gap-3 pointer-events-auto">
        <img
          src="/kairos-icon.png"
          alt="Kairos"
          className="h-9 w-9 rounded-xl ring-1 ring-line"
        />
        <div className="hidden sm:block font-display font-semibold text-lg text-ink tracking-tight">
          Kairos
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center gap-2 sm:gap-3 pointer-events-auto min-w-0">
        <button
          onClick={toggleSidebar}
          className="flex items-center gap-2 h-10 px-3 sm:px-4 rounded-full bg-surface/90 backdrop-blur ring-1 ring-line text-sm text-ink hover:ring-amber/60 transition-colors shrink-0"
          aria-label="New analysis"
        >
          <Menu size={16} className="text-dim" />
          <span className="hidden sm:inline">Menu</span>
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
            onKeyDown={onSearchKeyDown}
            onFocus={() => suggestions.length > 0 && setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 120)}
            placeholder="Search locations…"
            role="combobox"
            aria-expanded={open}
            aria-autocomplete="list"
            className="w-full h-10 pl-10 pr-14 rounded-full bg-surface/90 backdrop-blur ring-1 ring-line text-sm text-ink placeholder-dim outline-none focus:ring-amber/60 transition-shadow"
          />
          <kbd className="hidden sm:block absolute right-3 top-1/2 -translate-y-1/2 font-mono text-[10px] text-dim bg-raised px-1.5 py-0.5 rounded ring-1 ring-line">
            {searching ? "…" : "⌘K"}
          </kbd>

          {open && suggestions.length > 0 && (
            <ul className="absolute top-12 inset-x-0 z-40 max-h-72 overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel py-1.5">
              {suggestions.map((s, i) => (
                <li key={s.id}>
                  <button

                    onMouseDown={(e) => {
                      e.preventDefault();
                      pick(s);
                    }}
                    onMouseEnter={() => setActiveIndex(i)}
                    className={`w-full text-left flex items-center gap-2.5 px-4 py-2 text-sm transition-colors ${
                      i === activeIndex
                        ? "bg-raised text-ink"
                        : "text-dim hover:text-ink"
                    }`}
                  >
                    <MapPin size={14} className="shrink-0 text-teal" />
                    <span className="truncate">{s.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3 pointer-events-auto">
        <button
          onClick={() => {
            location.hash = "watch";
            location.reload();
          }}
          title="Live Watch: active disasters worldwide"
          className="hidden md:grid h-10 px-3.5 grid-flow-col items-center gap-1.5 rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-amber transition-colors"
        >
          <Radio size={15} className="text-amber" />
          <span className="text-xs font-medium">Live Watch</span>
        </button>
        <button
          onClick={() => {
            location.hash = "guardian";
            location.reload();
          }}
          title="Guardian: help spot illegal activity from space"
          className="hidden md:grid h-10 px-3.5 grid-flow-col items-center gap-1.5 rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-teal transition-colors"
        >
          <Shield size={15} className="text-teal" />
          <span className="text-xs font-medium">Guardian</span>
        </button>
        <button
          onClick={() => setTutorialOpen(true)}
          title="How to use Kairos"
          className="hidden md:grid h-10 w-10 place-items-center rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-ink transition-colors"
        >
          <HelpCircle size={17} />
        </button>
        <div className="relative md:hidden">
          <button
            onClick={() => setMoreOpen((v) => !v)}
            title="More"
            aria-label="More options"
            aria-expanded={moreOpen}
            className="h-10 w-10 grid place-items-center rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-ink transition-colors"
          >
            <MoreVertical size={17} />
          </button>
          {moreOpen && (
            <div className="absolute right-0 top-12 z-50 w-48 rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel py-1.5">
              <button
                onClick={() => {
                  location.hash = "watch";
                  location.reload();
                }}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-dim hover:text-ink"
              >
                <Radio size={15} className="text-amber" /> Live Watch
              </button>
              <button
                onClick={() => {
                  location.hash = "guardian";
                  location.reload();
                }}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-dim hover:text-ink"
              >
                <Shield size={15} className="text-teal" /> Guardian
              </button>
              <button
                onClick={() => {
                  setMoreOpen(false);
                  setTutorialOpen(true);
                }}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-dim hover:text-ink"
              >
                <HelpCircle size={15} /> How to use Kairos
              </button>
            </div>
          )}
        </div>
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
