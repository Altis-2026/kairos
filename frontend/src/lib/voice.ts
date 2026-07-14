/**
 * Voice for Janus — speech in, speech out, entirely in the browser.
 *
 * Uses the Web Speech API (SpeechRecognition + SpeechSynthesis), which ships
 * free in Chrome/Edge/Safari, so voice mode costs nothing and needs no API
 * key. docs/JANUS.md v2 notes a premium neural-TTS upgrade path (ElevenLabs /
 * OpenAI TTS) for later; this is the zero-cost foundation it slots into.
 *
 * Everything here degrades gracefully: isSpeechSupported() / isTTSSupported()
 * gate the UI so unsupported browsers simply don't show the mic / speaker.
 */

// The vendor-prefixed constructor isn't in the TS DOM lib; declare what we use.
interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
}
interface SpeechRecognitionEventLike {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

function getRecognitionCtor(): SpeechRecognitionCtor | null {
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export function isSpeechSupported(): boolean {
  return getRecognitionCtor() !== null;
}

export function isTTSSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/**
 * One push-to-talk dictation. Resolves with the recognized transcript (or ""
 * if nothing was heard). Returns a stop() handle so the caller can end it.
 */
export function startDictation(handlers: {
  onFinal: (text: string) => void;
  onInterim?: (text: string) => void;
  onError?: (error: string) => void;
  onEnd?: () => void;
}): { stop: () => void } | null {
  const Ctor = getRecognitionCtor();
  if (!Ctor) return null;

  const recognition = new Ctor();
  recognition.lang = navigator.language || "en-US";
  recognition.continuous = false;
  recognition.interimResults = true;

  let finalText = "";
  recognition.onresult = (event) => {
    let interim = "";
    for (let i = 0; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      // A result is "final" once the engine commits it; the interim/final
      // split isn't exposed on our minimal type, so we accumulate both and
      // let onInterim show live text while onFinal gets the whole utterance.
      interim += transcript;
    }
    finalText = interim;
    handlers.onInterim?.(interim);
  };
  recognition.onerror = (event) => handlers.onError?.(event.error);
  recognition.onend = () => {
    if (finalText.trim()) handlers.onFinal(finalText.trim());
    handlers.onEnd?.();
  };

  try {
    recognition.start();
  } catch {
    return null;
  }
  return { stop: () => recognition.stop() };
}

/** Strip the mentor's markdown-lite so TTS reads clean prose, not "hash hash". */
export function speakableText(markdown: string): string {
  return markdown
    .replace(/^#+\s*/gm, "") // headers
    .replace(/^[-*]\s+/gm, "") // bullets
    .replace(/\*\*/g, "")
    .replace(/`/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

let _voice: SpeechSynthesisVoice | null = null;

function pickVoice(): SpeechSynthesisVoice | null {
  if (_voice) return _voice;
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;
  // Prefer a natural-sounding English voice; fall back to the first available.
  _voice =
    voices.find((v) => /en/i.test(v.lang) && /natural|google|samantha/i.test(v.name)) ||
    voices.find((v) => /en/i.test(v.lang)) ||
    voices[0];
  return _voice;
}

export function speak(text: string) {
  if (!isTTSSupported()) return;
  const synth = window.speechSynthesis;
  synth.cancel(); // never let two replies overlap
  const utterance = new SpeechSynthesisUtterance(speakableText(text));
  const voice = pickVoice();
  if (voice) utterance.voice = voice;
  utterance.rate = 1.02;
  utterance.pitch = 1.0;
  synth.speak(utterance);
}

export function stopSpeaking() {
  if (isTTSSupported()) window.speechSynthesis.cancel();
}
