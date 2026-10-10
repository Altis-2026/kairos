import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BookOpen,
  CloudOff,
  Download,
  Eye,
  GraduationCap,
  Home,
  Landmark,
  Radar,
  Radio,
  ShieldCheck,
  Waves,
} from "lucide-react";
import KairosMark from "../KairosMark";
import { ANALYSIS_COLORS, fetchFeed, timeAgo, type Finding } from "../../api/feed";
import { fetchRegistry } from "../../api/registry";
import { fetchFeatured, type FeaturedStory } from "../../api/featured";
import { queueStory } from "../../lib/featured";
import { navigate } from "../../lib/navigation";
import { useMapStore } from "../../stores/mapStore";
import { usePrefsStore, type Locale } from "../../stores/prefsStore";

const COPY = {
  en: {
    eyebrow: "FREE SATELLITE RADAR FOR EVERYONE",
    title1: "See through the clouds.",
    title2: "Ask the Earth anything.",
    lede: "Kairos turns a plain question into a real measurement from space. It reads radar from Europe's Sentinel-1 satellites, which see through storms, smoke and darkness, then explains the answer, simulates what could happen next, and helps you prepare.",
    launch: "Launch Kairos",
    myPlace: "Check my place",
    myDistrict: "My district",
    trust: "Free · No account · Works on any device",
    statAnalyses: "analyses",
    statSims: "physics simulations",
    statCoverage: "of Earth covered",
    statRevisit: "day radar revisit",
    whyEyebrow: "WHY RADAR",
    whyTitle: "The storm that floods a town also blinds the cameras watching it.",
    whyBody:
      "In July 2025 the Guadalupe River rose about 26 feet in under an hour and more than 135 people died in the Texas Hill Country. Clouds hid the flooding from camera satellites. Radar saw straight through, and the data was free, but reading it took specialist software and training. Kairos makes it as easy as asking.",
    cameraTitle: "Camera satellites",
    cameraBody: "Blocked by clouds, smoke and night. Useless in the first hours of most disasters.",
    radarTitle: "Radar satellites",
    radarBody:
      "Send their own microwave pulse and time the echo. Water, fire scars and damage show up in any weather.",
    pillarsEyebrow: "ONE APP, FOUR JOBS",
    pillarsTitle: "Observe, simulate, prepare, learn.",
    observe: "Observe",
    observeBody:
      "Ask about any place and date. Floods, fires, ships, oil spills, deforestation, sinking ground, crops, air quality and more, measured from real radar scenes.",
    simulate: "Simulate",
    simulateBody:
      "Run a flood or a wildfire over real terrain with physics models and watch it unfold in 3D, clearly labelled as a simulation.",
    prepare: "Prepare",
    prepareBody:
      "Check your own address, see decades of hazard history, get a preparedness checklist, or print a briefing for any congressional district.",
    learn: "Learn",
    learnBody:
      "Short lessons on how radar sees the Earth, narrated real cases, a quiz, and Janus, a research mentor that runs analyses with you.",
    storiesEyebrow: "FEATURED STORIES",
    storiesTitle: "Real disasters, measured from space.",
    storiesBody: "Each one opens the globe and loads the actual radar result.",
    open: "Open",
    howEyebrow: "HOW IT WORKS",
    howTitle: "From a question to a map in about thirty seconds.",
    steps: [
      ["You ask", "Type or say a question in English or Spanish, or pick a place on the globe."],
      [
        "Kairos plans it",
        "A language model picks the analysis, the place and the dates, and asks you if anything is unclear.",
      ],
      [
        "Earth Engine measures it",
        "The radar scenes are processed on Google's servers. Nothing is downloaded, which is why this is free.",
      ],
      [
        "You see the answer",
        "A map layer, a headline number, a confidence score and a plain explanation, with the reasoning one tap away.",
      ],
    ],
    liveEyebrow: "FOUND ON ITS OWN",
    liveTitle: "Kairos watches active disasters by itself.",
    liveBody:
      "Every few hours it checks active events from NASA and a watchlist of hotspots, runs the analyses, and posts what it finds.",
    openWatch: "Open Live Watch",
    builtEyebrow: "BUILT BY",
    builtBody: "Students at Flower Mound High School in Flower Mound, Texas.",
    cta: "The data to see a disaster through the clouds was always free. Now anyone can use it.",
    about: "About",
    academy: "Academy",
    watch: "Live Watch",
    source: "Source code",
    install: "Install app",
    credit:
      "Contains modified Copernicus Sentinel data. Processing by Google Earth Engine. Basemaps by Mapbox.",
    typed: [
      "was there flooding near Kerrville in July 2025?",
      "how many ships are in the Strait of Hormuz today?",
      "what if the Trinity River flooded in Dallas?",
      "how much of Rondônia was cleared this year?",
      "is the ground sinking in Mexico City?",
    ],
  },
  es: {
    eyebrow: "RADAR SATELITAL GRATIS PARA TODOS",
    title1: "Mira a través de las nubes.",
    title2: "Pregúntale a la Tierra.",
    lede: "Kairos convierte una pregunta sencilla en una medición real desde el espacio. Lee el radar de los satélites Sentinel-1 de Europa, que ven a través de tormentas, humo y oscuridad, explica la respuesta, simula lo que podría pasar y te ayuda a prepararte.",
    launch: "Abrir Kairos",
    myPlace: "Revisar mi casa",
    myDistrict: "Mi distrito",
    trust: "Gratis · Sin cuenta · Funciona en cualquier dispositivo",
    statAnalyses: "análisis",
    statSims: "simulaciones físicas",
    statCoverage: "de la Tierra cubierta",
    statRevisit: "días entre pasadas",
    whyEyebrow: "POR QUÉ RADAR",
    whyTitle: "La tormenta que inunda un pueblo también ciega a las cámaras que lo observan.",
    whyBody:
      "En julio de 2025 el río Guadalupe subió unos 8 metros en menos de una hora y más de 135 personas murieron en el Hill Country de Texas. Las nubes ocultaron la inundación a los satélites con cámara. El radar veía a través de ellas y los datos eran gratuitos, pero leerlos requería software y formación especializada. Kairos lo hace tan fácil como preguntar.",
    cameraTitle: "Satélites con cámara",
    cameraBody:
      "Bloqueados por nubes, humo y la noche. Inútiles en las primeras horas de casi todos los desastres.",
    radarTitle: "Satélites de radar",
    radarBody:
      "Envían su propio pulso de microondas y miden el eco. El agua, las quemas y los daños aparecen con cualquier clima.",
    pillarsEyebrow: "UNA APP, CUATRO TAREAS",
    pillarsTitle: "Observar, simular, prepararse, aprender.",
    observe: "Observar",
    observeBody:
      "Pregunta por cualquier lugar y fecha. Inundaciones, incendios, barcos, derrames, deforestación, hundimiento del suelo, cultivos, calidad del aire y más.",
    simulate: "Simular",
    simulateBody:
      "Simula una inundación o un incendio sobre terreno real con modelos físicos y míralo en 3D, siempre marcado como simulación.",
    prepare: "Prepararse",
    prepareBody:
      "Revisa tu dirección, consulta décadas de historial de riesgos, obtén una lista de preparación o imprime un informe de cualquier distrito del Congreso.",
    learn: "Aprender",
    learnBody:
      "Lecciones cortas sobre cómo el radar ve la Tierra, casos reales narrados, un cuestionario y Janus, un mentor de investigación.",
    storiesEyebrow: "HISTORIAS DESTACADAS",
    storiesTitle: "Desastres reales, medidos desde el espacio.",
    storiesBody: "Cada una abre el globo y carga el resultado real del radar.",
    open: "Abrir",
    howEyebrow: "CÓMO FUNCIONA",
    howTitle: "De una pregunta a un mapa en unos treinta segundos.",
    steps: [
      ["Preguntas", "Escribe o di una pregunta en español o inglés, o elige un lugar en el globo."],
      [
        "Kairos lo planea",
        "Un modelo de lenguaje elige el análisis, el lugar y las fechas, y te pregunta si algo no está claro.",
      ],
      [
        "Earth Engine lo mide",
        "Las imágenes de radar se procesan en los servidores de Google. No se descarga nada, por eso es gratis.",
      ],
      [
        "Ves la respuesta",
        "Una capa en el mapa, una cifra principal, un nivel de confianza y una explicación clara.",
      ],
    ],
    liveEyebrow: "LO ENCUENTRA SOLO",
    liveTitle: "Kairos vigila los desastres activos por su cuenta.",
    liveBody:
      "Cada pocas horas revisa los eventos activos de la NASA y una lista de puntos críticos, corre los análisis y publica lo que encuentra.",
    openWatch: "Abrir En vivo",
    builtEyebrow: "CREADO POR",
    builtBody: "Estudiantes de Flower Mound High School en Flower Mound, Texas.",
    cta: "Los datos para ver un desastre a través de las nubes siempre fueron gratuitos. Ahora cualquiera puede usarlos.",
    about: "Acerca de",
    academy: "Academia",
    watch: "En vivo",
    source: "Código fuente",
    install: "Instalar app",
    credit:
      "Contiene datos modificados de Copernicus Sentinel. Procesamiento con Google Earth Engine. Mapas base de Mapbox.",
    typed: [
      "¿hubo inundaciones cerca de Kerrville en julio de 2025?",
      "¿cuántos barcos hay hoy en el estrecho de Ormuz?",
      "¿y si el río Trinity se desbordara en Dallas?",
      "¿cuánto bosque se taló en Rondônia este año?",
      "¿se está hundiendo el suelo en la Ciudad de México?",
    ],
  },
} as const;

const FALLBACK_STORIES: Pick<FeaturedStory, "id" | "title" | "place" | "when">[] = [
  {
    id: "hill-country-2025",
    title: "Texas Hill Country floods",
    place: "Kerr County, Texas",
    when: "July 2025",
  },
  { id: "pakistan-2022", title: "Pakistan monsoon floods", place: "Sindh, Pakistan", when: "August 2022" },
  { id: "lahaina-2023", title: "Lahaina wildfire", place: "Maui, Hawaii", when: "August 2023" },
  { id: "antakya-2023", title: "Turkey earthquake damage", place: "Antakya, Turkey", when: "February 2023" },
  { id: "rondonia-clearing", title: "Amazon clearing", place: "Rondonia, Brazil", when: "2020 dry season" },
  { id: "hunga-tonga-2022", title: "Hunga Tonga eruption", place: "Tonga", when: "January 2022" },
];

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
}

function useTypewriter(lines: readonly string[]): string {
  const [text, setText] = useState("");
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setText(lines[0]);
      return;
    }
    let line = 0;
    let char = 0;
    let deleting = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = () => {
      const current = lines[line];
      if (!deleting) {
        char++;
        setText(current.slice(0, char));
        deleting = char === current.length;
        timer = setTimeout(tick, deleting ? 1800 : 42);
      } else {
        char--;
        setText(current.slice(0, char));
        if (char === 0) {
          deleting = false;
          line = (line + 1) % lines.length;
          timer = setTimeout(tick, 350);
        } else {
          timer = setTimeout(tick, 18);
        }
      }
    };
    timer = setTimeout(tick, 700);
    return () => clearTimeout(timer);
  }, [lines]);
  return text;
}

function starField(count: number, seed: number): string {
  let s = seed;
  const rand = () => {
    s = (s * 16807) % 2147483647;
    return s / 2147483647;
  };
  return Array.from({ length: count }, () => {
    const x = Math.round(rand() * 1600);
    const y = Math.round(rand() * 1000);
    const o = (0.15 + rand() * 0.55).toFixed(2);
    return `${x}px ${y}px 0 0 rgba(232,239,233,${o})`;
  }).join(", ");
}

const reveal = {
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.5, ease: "easeOut" as const },
};

function RadarSweep() {
  const blips = [
    { top: "22%", left: "61%", delay: "0.4s" },
    { top: "48%", left: "78%", delay: "1.5s" },
    { top: "66%", left: "34%", delay: "2.6s" },
    { top: "35%", left: "25%", delay: "3.4s" },
  ];
  return (
    <div
      aria-hidden="true"
      className="relative aspect-square w-[240px] sm:w-[320px] lg:w-[420px] select-none"
    >
      {[0, 16, 32, 48].map((inset, i) => (
        <div
          key={inset}
          className="absolute rounded-full border"
          style={{ inset: `${inset}%`, borderColor: `rgba(0,191,168,${0.25 - i * 0.05})` }}
        />
      ))}
      <div className="absolute left-1/2 top-0 bottom-0 w-px bg-teal/10" />
      <div className="absolute top-1/2 left-0 right-0 h-px bg-teal/10" />
      <div className="absolute inset-0 rounded-full radar-sweep" />
      <div className="absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-teal shadow-glow" />
      {blips.map((b, i) => (
        <div
          key={i}
          className="absolute h-1.5 w-1.5 rounded-full bg-teal radar-blip"
          style={{ top: b.top, left: b.left, animationDelay: b.delay }}
        />
      ))}
    </div>
  );
}

function SectionHead({ eyebrow, title, body }: { eyebrow: string; title: string; body?: string }) {
  return (
    <motion.div {...reveal} className="max-w-2xl">
      <p className="font-mono text-[11px] tracking-[0.3em] text-teal">{eyebrow}</p>
      <h2 className="mt-3 font-display text-2xl sm:text-4xl font-semibold leading-tight">{title}</h2>
      {body && <p className="mt-3 text-dim leading-relaxed">{body}</p>}
    </motion.div>
  );
}

export default function Landing({ onLaunch }: { onLaunch: () => void }) {
  const locale = usePrefsStore((s) => s.locale);
  const setLocale = usePrefsStore((s) => s.setLocale);
  const c = COPY[locale];
  const typed = useTypewriter(c.typed);
  const [installEvent, setInstallEvent] = useState<InstallPromptEvent | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [stories, setStories] = useState<FeaturedStory[] | null>(null);
  const [analysisCount, setAnalysisCount] = useState(26);
  const starsSmall = useMemo(() => starField(90, 1337), []);
  const starsBright = useMemo(() => starField(30, 4242), []);

  useEffect(() => {
    fetchFeed(3)
      .then((d) => setFindings(d.findings.slice(0, 3)))
      .catch(() => undefined);
    fetchRegistry()
      .then((types) => types.length && setAnalysisCount(types.length))
      .catch(() => undefined);
    fetchFeatured()
      .then((d) => setStories(d.stories))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setInstallEvent(e as InstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  function openPanel(panel: string) {
    useMapStore.getState().requestPanel(panel);
    onLaunch();
  }

  function openStory(id: string) {
    const story = stories?.find((s) => s.id === id);
    if (story) queueStory(story);
    onLaunch();
  }

  const pillars = [
    { icon: Eye, title: c.observe, body: c.observeBody, action: onLaunch },
    { icon: Waves, title: c.simulate, body: c.simulateBody, action: () => openPanel("simulation") },
    { icon: ShieldCheck, title: c.prepare, body: c.prepareBody, action: () => openPanel("myplace") },
    { icon: GraduationCap, title: c.learn, body: c.learnBody, action: () => navigate("academy") },
  ];

  const storyCards = stories ?? FALLBACK_STORIES;

  return (
    <div className="h-full overflow-y-auto overflow-x-hidden bg-bg text-ink">
      <section className="relative flex min-h-[100dvh] flex-col px-5 sm:px-10">
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
          <div
            className="absolute inset-0 bg-cover bg-center opacity-40"
            style={{ backgroundImage: "url(/hero-orbital.png)" }}
          />
          <div className="absolute inset-0 bg-gradient-to-r from-bg via-bg/60 to-bg/20" />
          <div className="absolute inset-0 bg-gradient-to-t from-bg via-transparent to-bg/40" />
          <span className="absolute h-px w-px rounded-full" style={{ boxShadow: starsSmall }} />
          <span
            className="absolute h-[1.5px] w-[1.5px] rounded-full star-twinkle"
            style={{ boxShadow: starsBright }}
          />
        </div>

        <header className="relative z-10 flex h-16 items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-surface/80 ring-1 ring-line text-[#C9E6F7]">
            <KairosMark size={24} />
          </span>
          <span className="font-display text-lg font-semibold tracking-tight">Kairos</span>
          <nav className="ml-auto flex items-center gap-1 sm:gap-2 text-sm">
            <button
              onClick={() => navigate("watch")}
              className="hidden sm:inline px-3 py-2 text-dim hover:text-ink transition"
            >
              {c.watch}
            </button>
            <button
              onClick={() => navigate("academy")}
              className="hidden sm:inline px-3 py-2 text-dim hover:text-ink transition"
            >
              {c.academy}
            </button>
            <button
              onClick={() => navigate("about")}
              className="px-3 py-2 text-dim hover:text-ink transition"
            >
              {c.about}
            </button>
            <button
              onClick={() => setLocale((locale === "en" ? "es" : "en") as Locale)}
              className="h-9 px-3 rounded-full ring-1 ring-line text-xs font-semibold text-dim hover:text-ink transition"
              aria-label={locale === "en" ? "Ver en español" : "View in English"}
            >
              {locale === "en" ? "ES" : "EN"}
            </button>
          </nav>
        </header>

        <div className="relative z-10 flex flex-1 flex-col items-center justify-center gap-10 py-10 lg:flex-row lg:gap-16">
          <div className="max-w-xl text-center lg:text-left">
            <p className="font-mono text-[11px] tracking-[0.3em] text-teal">{c.eyebrow}</p>
            <h1 className="mt-4 font-display text-4xl font-bold leading-[1.08] sm:text-6xl">
              {c.title1}
              <br />
              <span className="text-teal">{c.title2}</span>
            </h1>
            <div className="mx-auto mt-6 flex h-12 max-w-lg items-center gap-3 rounded-2xl bg-surface/80 px-5 ring-1 ring-line backdrop-blur lg:mx-0">
              <span className="h-2 w-2 shrink-0 rounded-full bg-teal animate-pulse-soft" />
              <span className="min-w-0 truncate text-left text-sm text-ink">
                {typed}
                <span className="typing-caret" aria-hidden="true" />
              </span>
            </div>
            <p className="mx-auto mt-5 max-w-lg text-[15px] leading-relaxed text-dim lg:mx-0">{c.lede}</p>
            <div className="mt-7 flex flex-wrap justify-center gap-3 lg:justify-start">
              <button
                onClick={onLaunch}
                className="inline-flex h-12 items-center gap-2 rounded-full bg-amber px-7 font-medium text-bg shadow-panel transition hover:brightness-110"
              >
                {c.launch} <ArrowRight size={16} />
              </button>
              <button
                onClick={() => openPanel("myplace")}
                className="inline-flex h-12 items-center gap-2 rounded-full bg-surface/80 px-5 text-sm ring-1 ring-line backdrop-blur transition hover:ring-teal/60"
              >
                <Home size={15} className="text-teal" /> {c.myPlace}
              </button>
              <button
                onClick={() => openPanel("district")}
                className="inline-flex h-12 items-center gap-2 rounded-full bg-surface/80 px-5 text-sm ring-1 ring-line backdrop-blur transition hover:ring-teal/60"
              >
                <Landmark size={15} className="text-teal" /> {c.myDistrict}
              </button>
            </div>
            <p className="mt-4 text-xs text-dim">{c.trust}</p>
            {installEvent && (
              <button
                onClick={() => installEvent.prompt()}
                className="mt-3 inline-flex items-center gap-1.5 text-xs text-teal hover:underline"
              >
                <Download size={13} /> {c.install}
              </button>
            )}
          </div>
          <RadarSweep />
        </div>

        <div className="relative z-10 mx-auto mb-8 grid w-full max-w-4xl grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            [String(analysisCount), c.statAnalyses],
            ["2", c.statSims],
            ["100%", c.statCoverage],
            ["6–12", c.statRevisit],
          ].map(([value, label]) => (
            <div
              key={label}
              className="rounded-2xl bg-surface/70 px-4 py-3 text-center ring-1 ring-line backdrop-blur"
            >
              <div className="font-display text-2xl text-teal">{value}</div>
              <div className="text-[11px] text-dim">{label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="px-5 py-20 sm:px-10">
        <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-2">
          <div>
            <SectionHead eyebrow={c.whyEyebrow} title={c.whyTitle} />
            <motion.p {...reveal} className="mt-4 max-w-xl leading-relaxed text-dim">
              {c.whyBody}
            </motion.p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <motion.div {...reveal} className="rounded-3xl bg-surface p-6 ring-1 ring-line">
              <CloudOff className="text-dim" size={22} />
              <h3 className="mt-4 font-display text-lg">{c.cameraTitle}</h3>
              <p className="mt-2 text-sm leading-relaxed text-dim">{c.cameraBody}</p>
            </motion.div>
            <motion.div {...reveal} className="rounded-3xl bg-surface p-6 ring-1 ring-teal/40 shadow-glow">
              <Radar className="text-teal" size={22} />
              <h3 className="mt-4 font-display text-lg">{c.radarTitle}</h3>
              <p className="mt-2 text-sm leading-relaxed text-dim">{c.radarBody}</p>
            </motion.div>
          </div>
        </div>
      </section>

      <section className="px-5 py-20 sm:px-10 bg-surface/40 border-y border-line">
        <div className="mx-auto max-w-6xl">
          <SectionHead eyebrow={c.pillarsEyebrow} title={c.pillarsTitle} />
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {pillars.map(({ icon: Icon, title, body, action }) => (
              <motion.button
                {...reveal}
                key={title}
                onClick={action}
                className="group flex flex-col rounded-3xl bg-bg p-6 text-left ring-1 ring-line transition hover:ring-teal/50"
              >
                <span className="grid h-11 w-11 place-items-center rounded-2xl bg-raised text-teal ring-1 ring-teal/30">
                  <Icon size={20} />
                </span>
                <h3 className="mt-5 font-display text-xl">{title}</h3>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-dim">{body}</p>
                <ArrowRight
                  size={16}
                  className="mt-5 text-dim transition group-hover:translate-x-1 group-hover:text-teal"
                />
              </motion.button>
            ))}
          </div>
        </div>
      </section>

      <section className="px-5 py-20 sm:px-10">
        <div className="mx-auto max-w-6xl">
          <SectionHead eyebrow={c.storiesEyebrow} title={c.storiesTitle} body={c.storiesBody} />
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {storyCards.map((s) => (
              <motion.button
                {...reveal}
                key={s.id}
                onClick={() => openStory(s.id)}
                className="group rounded-3xl bg-surface p-5 text-left ring-1 ring-line transition hover:ring-amber/50"
              >
                <div className="font-mono text-[10px] tracking-[0.2em] text-amber uppercase">{s.when}</div>
                <h3 className="mt-2 font-display text-lg">{s.title}</h3>
                <p className="text-xs text-dim">{s.place}</p>
                {"summary" in s && typeof s.summary === "string" && (
                  <p className="mt-3 text-sm leading-relaxed text-dim">{s.summary}</p>
                )}
                <span className="mt-4 inline-flex items-center gap-1.5 text-xs text-teal">
                  {c.open} <ArrowRight size={13} className="transition group-hover:translate-x-1" />
                </span>
              </motion.button>
            ))}
          </div>
        </div>
      </section>

      <section className="px-5 py-20 sm:px-10 bg-surface/40 border-y border-line">
        <div className="mx-auto max-w-6xl">
          <SectionHead eyebrow={c.howEyebrow} title={c.howTitle} />
          <ol className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {c.steps.map(([title, body], i) => (
              <motion.li {...reveal} key={title} className="rounded-3xl bg-bg p-6 ring-1 ring-line">
                <span className="font-mono text-xs text-amber">0{i + 1}</span>
                <h3 className="mt-3 font-display text-lg">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-dim">{body}</p>
              </motion.li>
            ))}
          </ol>
        </div>
      </section>

      {findings.length > 0 && (
        <section className="px-5 py-20 sm:px-10">
          <div className="mx-auto max-w-6xl">
            <SectionHead eyebrow={c.liveEyebrow} title={c.liveTitle} body={c.liveBody} />
            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              {findings.map((f) => (
                <motion.div {...reveal} key={f.id} className="rounded-3xl bg-surface p-5 ring-1 ring-line">
                  <div className="flex items-center gap-2 text-xs text-dim">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ background: ANALYSIS_COLORS[f.analysis_type] ?? "#00BFA8" }}
                    />
                    {f.display_name}
                    <span className="ml-auto font-mono">{timeAgo(f.created_at)}</span>
                  </div>
                  <div className="mt-2 font-display text-lg">{f.region}</div>
                  {f.headline_value != null && (
                    <div className="mt-1 text-sm text-teal">
                      {Math.round(f.headline_value).toLocaleString()} {f.headline_unit}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
            <button
              onClick={() => navigate("watch")}
              className="mt-8 inline-flex items-center gap-2 rounded-full bg-surface px-5 h-11 text-sm ring-1 ring-line transition hover:ring-amber/60"
            >
              <Radio size={15} className="text-amber" /> {c.openWatch}
            </button>
          </div>
        </section>
      )}

      <section className="px-5 py-24 sm:px-10">
        <motion.div {...reveal} className="mx-auto max-w-3xl text-center">
          <p className="font-mono text-[11px] tracking-[0.3em] text-teal">{c.builtEyebrow}</p>
          <h2 className="mt-3 font-display text-3xl sm:text-4xl font-semibold">
            Amogh Vinaykumar & Prem Kamasani
          </h2>
          <p className="mt-3 text-dim">{c.builtBody}</p>
          <p className="mx-auto mt-8 max-w-xl text-lg leading-relaxed">{c.cta}</p>
          <button
            onClick={onLaunch}
            className="mt-8 inline-flex h-12 items-center gap-2 rounded-full bg-amber px-8 font-medium text-bg shadow-panel transition hover:brightness-110"
          >
            {c.launch} <ArrowRight size={16} />
          </button>
        </motion.div>
      </section>

      <footer className="border-t border-line px-5 py-8 sm:px-10">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 text-xs text-dim sm:flex-row sm:items-center">
          <div className="flex items-center gap-2">
            <KairosMark size={18} />
            <span>Kairos · Amogh Vinaykumar & Prem Kamasani</span>
          </div>
          <div className="flex flex-wrap gap-4 sm:ml-auto">
            <button onClick={() => navigate("about")} className="hover:text-ink">
              {c.about}
            </button>
            <button
              onClick={() => navigate("academy")}
              className="inline-flex items-center gap-1 hover:text-ink"
            >
              <BookOpen size={12} /> {c.academy}
            </button>
            <a
              href="https://github.com/Altis-2026/kairos"
              target="_blank"
              rel="noreferrer"
              className="hover:text-ink"
            >
              {c.source}
            </a>
          </div>
        </div>
        <p className="mx-auto mt-4 max-w-6xl text-[11px] text-dim/80">{c.credit}</p>
      </footer>
    </div>
  );
}
