import { create } from "zustand";

const SIMPLE_KEY = "kairos_simple_mode";
const SPEAK_KEY = "kairos_speak_replies";

function readFlag(key: string, fallback: boolean): boolean {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : v === "1";
  } catch {
    return fallback;
  }
}

function writeFlag(key: string, value: boolean) {
  try {
    localStorage.setItem(key, value ? "1" : "0");
  } catch {
    return;
  }
}

interface PrefsState {
  simpleMode: boolean;
  speakReplies: boolean;
  toggleSimpleMode: () => void;
  toggleSpeakReplies: () => void;
}

export const usePrefsStore = create<PrefsState>((set, get) => ({
  simpleMode: readFlag(SIMPLE_KEY, true),
  speakReplies: readFlag(SPEAK_KEY, false),
  toggleSimpleMode: () => {
    const next = !get().simpleMode;
    writeFlag(SIMPLE_KEY, next);
    set({ simpleMode: next });
  },
  toggleSpeakReplies: () => {
    const next = !get().speakReplies;
    writeFlag(SPEAK_KEY, next);
    set({ speakReplies: next });
  },
}));
