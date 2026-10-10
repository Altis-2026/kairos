import { create } from "zustand";

export type Locale = "en" | "es";

const SIMPLE_KEY = "kairos_simple_mode";
const SPEAK_KEY = "kairos_speak_replies";
const LOCALE_KEY = "kairos_locale";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    return;
  }
}

function initialLocale(): Locale {
  const saved = read(LOCALE_KEY);
  if (saved === "en" || saved === "es") return saved;
  const lang = typeof navigator === "undefined" ? "" : navigator.language;
  return lang?.toLowerCase().startsWith("es") ? "es" : "en";
}

interface PrefsState {
  simpleMode: boolean;
  speakReplies: boolean;
  locale: Locale;
  toggleSimpleMode: () => void;
  toggleSpeakReplies: () => void;
  setLocale: (locale: Locale) => void;
}

export const usePrefsStore = create<PrefsState>((set, get) => ({
  simpleMode: read(SIMPLE_KEY) !== "0",
  speakReplies: read(SPEAK_KEY) === "1",
  locale: initialLocale(),
  toggleSimpleMode: () => {
    const next = !get().simpleMode;
    write(SIMPLE_KEY, next ? "1" : "0");
    set({ simpleMode: next });
  },
  toggleSpeakReplies: () => {
    const next = !get().speakReplies;
    write(SPEAK_KEY, next ? "1" : "0");
    set({ speakReplies: next });
  },
  setLocale: (locale) => {
    write(LOCALE_KEY, locale);
    document.documentElement.lang = locale;
    set({ locale });
  },
}));
