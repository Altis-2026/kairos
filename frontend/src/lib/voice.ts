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

export function startDictation(handlers: {
  lang?: string;
  onFinal: (text: string) => void;
  onInterim?: (text: string) => void;
  onError?: (error: string) => void;
  onEnd?: () => void;
}): { stop: () => void } | null {
  const Ctor = getRecognitionCtor();
  if (!Ctor) return null;

  const recognition = new Ctor();
  recognition.lang = handlers.lang || navigator.language || "en-US";
  recognition.continuous = false;
  recognition.interimResults = true;

  let finalText = "";
  recognition.onresult = (event) => {
    let interim = "";
    for (let i = 0; i < event.results.length; i++) {
      interim += event.results[i][0].transcript;
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

export function speakableText(markdown: string): string {
  return markdown
    .replace(/^#+\s*/gm, "")
    .replace(/^[-*]\s+/gm, "")
    .replace(/\*\*/g, "")
    .replace(/`/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

const voiceCache = new Map<string, SpeechSynthesisVoice | null>();

function pickVoice(lang: string): SpeechSynthesisVoice | null {
  const prefix = lang.slice(0, 2).toLowerCase();
  if (voiceCache.has(prefix)) return voiceCache.get(prefix) ?? null;
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;
  const matching = voices.filter((v) => v.lang.toLowerCase().startsWith(prefix));
  const voice =
    matching.find((v) => /natural|google|samantha|paulina|monica/i.test(v.name)) || matching[0] || null;
  voiceCache.set(prefix, voice);
  return voice;
}

export function speak(text: string, lang = "en-US") {
  if (!isTTSSupported()) return;
  const synth = window.speechSynthesis;
  synth.cancel();
  const utterance = new SpeechSynthesisUtterance(speakableText(text));
  utterance.lang = lang;
  const voice = pickVoice(lang);
  if (voice) utterance.voice = voice;
  utterance.rate = 1.02;
  synth.speak(utterance);
}

export function stopSpeaking() {
  if (isTTSSupported()) window.speechSynthesis.cancel();
}
