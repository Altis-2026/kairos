import { usePrefsStore, type Locale } from "../stores/prefsStore";

const STRINGS = {
  en: {
    askPlaceholder: "Ask about anywhere on Earth…",
    listening: "Listening…",
    send: "Ask",
    stop: "Stop",
    conversation: "Conversation",
    hideConversation: "Hide conversation",
    showConversation: "Show conversation",
    newChat: "New chat",
    readAloud: "Read replies aloud",
    stopReading: "Stop reading replies aloud",
    askByVoice: "Ask by voice",
    stopListening: "Stop listening",
    whyThis: "Why this analysis",
    stage1: "Understanding your question",
    stage2: "Searching the Sentinel-1 archive",
    stage3: "Processing radar scenes on Earth Engine",
    stage4: "Writing the explanation",
    cancelled: "Stopped. Ask again whenever you like.",
    clarify: "Could you tell me a bit more?",
    done: "Done. The result is on the globe.",
    simulateHere: "Simulate a flood here",
    simulateFire: "Simulate a wildfire here",
    simulating: "Simulating…",
    confidence: "confidence",
    radarDate: "radar pass",
    suggestion1: "Flooding near Kerrville, Texas in July 2025",
    suggestion2: "Ships in the Strait of Hormuz this week",
    suggestion3: "What if the Trinity River flooded in Dallas?",
    suggestion4: "Deforestation in Rondonia, Brazil this year",
    followCompare: "Compare with the same time last year",
    followDamage: "Check building damage here too",
    followWorse: "What if it flooded worse here?",
    navWatch: "Live Watch",
    navGuardian: "Guardian",
    navForesight: "Foresight",
    navAcademy: "Academy",
    navAbout: "About",
    navGuide: "Guide",
    searchPlaceholder: "Search places…",
    signIn: "Sign in",
    signOut: "Sign out",
    backToGlobe: "Back to the globe",
    language: "Español",
  },
  es: {
    askPlaceholder: "Pregunta sobre cualquier lugar de la Tierra…",
    listening: "Escuchando…",
    send: "Preguntar",
    stop: "Detener",
    conversation: "Conversación",
    hideConversation: "Ocultar conversación",
    showConversation: "Mostrar conversación",
    newChat: "Nueva conversación",
    readAloud: "Leer respuestas en voz alta",
    stopReading: "Dejar de leer en voz alta",
    askByVoice: "Preguntar por voz",
    stopListening: "Dejar de escuchar",
    whyThis: "Por qué este análisis",
    stage1: "Entendiendo tu pregunta",
    stage2: "Buscando en el archivo de Sentinel-1",
    stage3: "Procesando imágenes de radar en Earth Engine",
    stage4: "Escribiendo la explicación",
    cancelled: "Detenido. Pregunta de nuevo cuando quieras.",
    clarify: "¿Puedes darme un poco más de detalle?",
    done: "Listo. El resultado está en el globo.",
    simulateHere: "Simular una inundación aquí",
    simulateFire: "Simular un incendio aquí",
    simulating: "Simulando…",
    confidence: "confianza",
    radarDate: "paso del radar",
    suggestion1: "Inundaciones cerca de Kerrville, Texas en julio de 2025",
    suggestion2: "Barcos en el estrecho de Ormuz esta semana",
    suggestion3: "¿Y si el río Trinity se desbordara en Dallas?",
    suggestion4: "Deforestación en Rondônia, Brasil este año",
    followCompare: "Comparar con la misma fecha del año pasado",
    followDamage: "Revisar también daños en edificios",
    followWorse: "¿Y si la inundación fuera peor aquí?",
    navWatch: "En vivo",
    navGuardian: "Guardián",
    navForesight: "Previsión",
    navAcademy: "Academia",
    navAbout: "Acerca de",
    navGuide: "Guía",
    searchPlaceholder: "Buscar lugares…",
    signIn: "Iniciar sesión",
    signOut: "Cerrar sesión",
    backToGlobe: "Volver al globo",
    language: "English",
  },
} as const;

export type StringKey = keyof (typeof STRINGS)["en"];

export function translate(locale: Locale, key: StringKey): string {
  return STRINGS[locale][key] ?? STRINGS.en[key];
}

export function useT() {
  const locale = usePrefsStore((s) => s.locale);
  return (key: StringKey) => translate(locale, key);
}

export function speechLang(locale: Locale): string {
  return locale === "es" ? "es-US" : "en-US";
}
