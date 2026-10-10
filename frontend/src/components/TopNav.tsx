import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import {
  ArrowLeft,
  GraduationCap,
  HelpCircle,
  Info,
  Menu,
  Search,
  LogIn,
  LogOut,
  MapPin,
  Radio,
  Shield,
  Telescope,
} from "lucide-react";
import { useMapStore } from "../stores/mapStore";
import { useSidebarStore } from "../stores/sidebarStore";
import { useAuthStore } from "../stores/authStore";
import { useIsCompact } from "../hooks/useIsCompact";
import KairosMark from "./KairosMark";
import { firebaseEnabled, signInWithGoogle, signOut } from "../lib/firebase";
import { navigate } from "../lib/navigation";
import { useT } from "../lib/i18n";
import { usePrefsStore } from "../stores/prefsStore";

const MAPBOX_TOKEN = (import.meta.env.VITE_MAPBOX_TOKEN as string) || "";

interface GeocodeFeature {
  id: string;
  place_name: string;
  center: number[];
  bbox?: number[];
}

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
  const [searchExpanded, setSearchExpanded] = useState(false);
  const isCompact = useIsCompact();
  const inputRef = useRef<HTMLInputElement>(null);

  const justPickedRef = useRef(false);
  const requestFlyTo = useMapStore((s) => s.requestFlyTo);
  const setTutorialOpen = useMapStore((s) => s.setTutorialOpen);
  const toggleSidebar = useSidebarStore((s) => s.toggleSidebar);
  const user = useAuthStore((s) => s.user);
  const t = useT();
  const locale = usePrefsStore((s) => s.locale);
  const setLocale = usePrefsStore((s) => s.setLocale);

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
        const features: GeocodeFeature[] = data.features ?? [];
        const next: Suggestion[] = features
          .filter((f) => Array.isArray(f.center))
          .map((f) => ({
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
    setSearchExpanded(false);
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
      setSearchExpanded(false);
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

  const searchBox = (
    <div className="relative w-full max-w-md">
      <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-dim" />
      <input
        ref={inputRef}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        onKeyDown={onSearchKeyDown}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        placeholder={t("searchPlaceholder")}
        aria-label={t("searchPlaceholder")}
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
        className="w-full h-10 pl-10 pr-14 rounded-full bg-surface/90 backdrop-blur ring-1 ring-line text-sm text-ink placeholder-dim outline-none focus:ring-amber/60 transition-shadow"
      />
      <kbd className="absolute right-3 top-1/2 -translate-y-1/2 font-mono text-[10px] text-dim bg-raised px-1.5 py-0.5 rounded ring-1 ring-line hidden lg:block">
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
                  i === activeIndex ? "bg-raised text-ink" : "text-dim hover:text-ink"
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
  );

  if (isCompact && searchExpanded) {
    return (
      <header className="absolute top-0 inset-x-0 z-30 flex items-center gap-2 px-3 h-16 pointer-events-none">
        <button
          onClick={() => {
            setSearchExpanded(false);
            setOpen(false);
          }}
          className="shrink-0 h-10 w-10 grid place-items-center rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-ink transition-colors pointer-events-auto"
          title={t("backToGlobe")}
          aria-label={t("backToGlobe")}
        >
          <ArrowLeft size={17} />
        </button>
        <div className="flex-1 pointer-events-auto">{searchBox}</div>
      </header>
    );
  }

  return (
    <header className="absolute top-0 inset-x-0 z-30 flex items-center gap-2 px-3 h-16 pointer-events-none lg:gap-4 lg:px-5">
      <div className="flex items-center gap-3 pointer-events-auto">
        <span className="h-9 w-9 shrink-0 grid place-items-center rounded-xl bg-surface/90 ring-1 ring-line text-[#C9E6F7]">
          <KairosMark size={24} title="Kairos" />
        </span>
        <div className="leading-tight hidden lg:block">
          <div className="font-display font-semibold text-lg text-ink tracking-tight">Kairos</div>
          <div className="font-mono text-[9px] tracking-[0.22em] text-dim">SATELLITE RADAR</div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center gap-2 lg:gap-3 pointer-events-auto min-w-0">
        <button
          onClick={toggleSidebar}
          title="Analysis wizard"
          aria-label="Open the analysis wizard"
          data-tour="menu"
          className="shrink-0 flex items-center gap-2 h-10 w-10 lg:w-auto justify-center lg:px-4 rounded-full bg-surface/90 backdrop-blur ring-1 ring-line text-sm text-ink hover:ring-amber/60 transition-colors"
        >
          <Menu size={16} className="text-dim" />
          <span className="hidden lg:inline">Menu</span>
        </button>
        {isCompact ? (
          <button
            onClick={() => {
              setSearchExpanded(true);
              requestAnimationFrame(() => inputRef.current?.focus());
            }}
            title={t("searchPlaceholder")}
            aria-label={t("searchPlaceholder")}
            className="shrink-0 h-10 w-10 grid place-items-center rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-ink transition-colors"
          >
            <Search size={16} />
          </button>
        ) : (
          searchBox
        )}
      </div>

      <div className="flex items-center gap-1.5 lg:gap-2 pointer-events-auto">
        {[
          {
            route: "watch",
            label: t("navWatch"),
            icon: Radio,
            tone: "text-amber",
            tour: "livewatch",
            wide: true,
          },
          { route: "foresight", label: t("navForesight"), icon: Telescope, tone: "text-teal", wide: true },
          { route: "academy", label: t("navAcademy"), icon: GraduationCap, tone: "text-teal", wide: false },
          { route: "guardian", label: t("navGuardian"), icon: Shield, tone: "text-teal", wide: false },
        ].map(({ route, label, icon: Icon, tone, tour, wide }) => (
          <button
            key={route}
            onClick={() => navigate(route)}
            title={label}
            aria-label={label}
            data-tour={tour}
            className={`h-10 w-10 xl:w-auto xl:px-3.5 ${wide ? "grid" : "hidden md:grid"} grid-flow-col items-center justify-center gap-1.5 rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-ink transition-colors`}
          >
            <Icon size={15} className={tone} />
            <span className="text-xs font-medium hidden xl:inline">{label}</span>
          </button>
        ))}
        <button
          onClick={() => setLocale(locale === "en" ? "es" : "en")}
          title={t("language")}
          aria-label={t("language")}
          className="h-10 w-10 shrink-0 grid place-items-center rounded-full bg-surface/90 ring-1 ring-line text-[11px] font-semibold text-dim hover:text-ink transition-colors"
        >
          {locale === "en" ? "ES" : "EN"}
        </button>
        <button
          onClick={() => navigate("about")}
          title={t("navAbout")}
          aria-label={t("navAbout")}
          className="h-10 w-10 shrink-0 hidden sm:grid place-items-center rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-ink transition-colors"
        >
          <Info size={16} />
        </button>
        <button
          onClick={() => setTutorialOpen(true)}
          title={t("navGuide")}
          aria-label={t("navGuide")}
          className="h-10 w-10 shrink-0 grid place-items-center rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-ink transition-colors"
        >
          <HelpCircle size={17} />
        </button>
        {user ? (
          <div className="flex items-center gap-2">
            {user.photoUrl ? (
              <img
                src={user.photoUrl}
                alt={user.name ?? "Account"}
                title={user.email ?? undefined}
                className="h-10 w-10 rounded-full ring-1 ring-teal/60 object-cover shrink-0"
              />
            ) : (
              <div className="h-10 w-10 shrink-0 grid place-items-center rounded-full bg-raised ring-1 ring-teal/60 font-display text-teal">
                {(user.name ?? "U").slice(0, 1)}
              </div>
            )}
            <button
              onClick={() => signOut()}
              title={t("signOut")}
              aria-label={t("signOut")}
              className="h-10 w-10 shrink-0 grid place-items-center rounded-full bg-surface/90 ring-1 ring-line text-dim hover:text-ink transition-colors"
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
            aria-label={t("signIn")}
            className="h-10 w-10 lg:w-auto lg:px-4 grid place-items-center lg:block rounded-full bg-amber text-bg font-medium text-sm hover:brightness-110 transition disabled:opacity-60 shrink-0"
          >
            <LogIn size={16} className="lg:hidden" />
            <span className="hidden lg:inline">{t("signIn")}</span>
          </button>
        )}
      </div>

      {authError && (
        <div className="absolute top-16 right-3 lg:right-5 max-w-xs bg-surface ring-1 ring-line rounded-xl p-3 text-xs text-dim pointer-events-auto shadow-panel">
          {authError}
        </div>
      )}
    </header>
  );
}
