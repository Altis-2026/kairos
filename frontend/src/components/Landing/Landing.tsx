import { useEffect, useMemo, useState } from "react";
import { MotionConfig, motion } from "framer-motion";
import {
  ArrowDown,
  ArrowRight,
  Building2,
  Download,
  Droplets,
  Flame,
  Radio,
  Ship,
  Snowflake,
  Sprout,
  Trees,
  Waves,
} from "lucide-react";
import { ANALYSIS_COLORS, fetchFeed, timeAgo, type Finding } from "../../api/feed";

const EXAMPLE_QUESTIONS = [
  "is there flooding near Dhaka right now?",
  "how many ships are in the Strait of Hormuz today?",
  "how much of Rondônia was cleared this year?",
  "did the burn scar grow overnight?",
  "how deep is the water in the flooded district?",
];

function useTypewriter(lines: string[]): string {
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
        if (char === current.length) {
          deleting = true;
          timer = setTimeout(tick, 1800);
        } else {
          timer = setTimeout(tick, 42);
        }
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

const reveal = {
  initial: { opacity: 0, y: 26 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.55, ease: "easeOut" as const },
};

const CAPABILITIES = [
  { icon: Waves, name: "Flood mapping", blurb: "New water where there was land yesterday" },
  { icon: Ship, name: "Ship detection", blurb: "Vessels at sea, counted day or night" },
  { icon: Flame, name: "Burn scars", blurb: "Fire damage mapped through the smoke" },
  { icon: Droplets, name: "Oil spills", blurb: "Slicks that flatten the sea surface" },
  { icon: Trees, name: "Deforestation", blurb: "Canopy loss against a 12-month baseline" },
  { icon: Snowflake, name: "Sea ice", blurb: "The ice edge, even in polar darkness" },
  { icon: Building2, name: "Quake damage", blurb: "Collapsed structures within hours" },
  { icon: Sprout, name: "Crop health", blurb: "Vegetation vigour when optical is blind" },
];

const STEPS = [
  {
    title: "You ask in plain language",
    body: "Type something like \"is there flooding near Dhaka right now?\" There are no forms to fill in unless you want them.",
  },
  {
    title: "Claude turns it into an analysis",
    body: "A language model reads the question and picks the analysis type, the place, and the date window. If it is unsure, it asks you instead of guessing.",
  },
  {
    title: "Earth Engine does the heavy lifting",
    body: "Google Earth Engine filters and processes the Sentinel-1 radar scenes server-side. Raw imagery never leaves the cloud, only a map layer and the statistics come back.",
  },
  {
    title: "The answer lands on the globe",
    body: "You get a coloured overlay, a headline number, a confidence score, and a plain explanation of what the radar actually saw.",
  },
];

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
}

function starField(count: number, seed: number): string {
  let s = seed;
  const rand = () => {
    s = (s * 16807) % 2147483647;
    return s / 2147483647;
  };
  const dots: string[] = [];
  for (let i = 0; i < count; i++) {
    const x = Math.round(rand() * 1600);
    const y = Math.round(rand() * 1000);
    const o = (0.15 + rand() * 0.55).toFixed(2);
    dots.push(`${x}px ${y}px 0 0 rgba(232,239,233,${o})`);
  }
  return dots.join(", ");
}

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
      className="relative aspect-square w-[260px] sm:w-[340px] lg:w-[430px] select-none"
    >
      <div className="absolute inset-0 rounded-full border border-teal/25" />
      <div className="absolute inset-[16%] rounded-full border border-teal/20" />
      <div className="absolute inset-[32%] rounded-full border border-teal/15" />
      <div className="absolute inset-[48%] rounded-full border border-teal/10" />
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

export default function Landing({ onLaunch }: { onLaunch: () => void }) {
  const [installEvent, setInstallEvent] = useState<InstallPromptEvent | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const starsSmall = useMemo(() => starField(90, 1337), []);
  const starsBright = useMemo(() => starField(30, 4242), []);
  const typed = useTypewriter(EXAMPLE_QUESTIONS);

  useEffect(() => {
    fetchFeed(3)
      .then((d) => setFindings(d.findings.slice(0, 3)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setInstallEvent(e as InstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  function openLiveWatch() {
    location.hash = "watch";
    location.reload();
  }

  return (
    <MotionConfig reducedMotion="user">
    <div className="h-full overflow-y-auto overflow-x-hidden bg-bg text-ink">
      <section className="relative flex min-h-[100dvh] flex-col px-6 sm:px-10">
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
          <div
            className="absolute inset-0 bg-cover bg-center opacity-40"
            style={{ backgroundImage: "url(/hero-orbital.png)" }}
          />
          <video
            className="absolute inset-0 h-full w-full object-cover opacity-40 motion-reduce:hidden"
            src="/hero-orbital.mp4"
            autoPlay
            muted
            loop
            playsInline
          />
          <div className="absolute inset-0 bg-gradient-to-r from-bg via-bg/60 to-bg/20" />
          <div className="absolute inset-0 bg-gradient-to-t from-bg via-transparent to-bg/40" />
          <span
            className="absolute h-px w-px rounded-full"
            style={{ boxShadow: starsSmall }}
          />
          <span
            className="absolute h-[1.5px] w-[1.5px] rounded-full star-twinkle"
            style={{ boxShadow: starsBright }}
          />
        </div>

        <header className="relative z-10 flex h-16 items-center gap-3">
          <img
            src="/kairos-icon.png"
            alt=""
            className="h-9 w-9 rounded-xl ring-1 ring-line"
          />
          <span className="font-display font-semibold text-lg tracking-tight">
            Kairos
          </span>
        </header>

        <div className="relative z-10 flex flex-1 flex-col items-center justify-center gap-10 py-10 lg:flex-row lg:gap-16">
          <div className="max-w-xl text-center lg:text-left">
            <p className="font-mono text-[11px] tracking-[0.3em] text-teal">
              SENTINEL-1 RADAR, ON DEMAND
            </p>
            <h1 className="mt-4 font-display text-4xl font-bold leading-tight sm:text-6xl">
              Ask the Earth a question.
              <br />
              <span className="text-teal">Get a radar answer.</span>
            </h1>
            <div className="mx-auto mt-6 flex h-12 max-w-lg items-center gap-3 rounded-2xl bg-surface/80 px-5 ring-1 ring-line backdrop-blur lg:mx-0">
              <span className="h-2 w-2 shrink-0 rounded-full bg-teal animate-pulse-soft" />
              <span className="min-w-0 truncate text-left text-sm text-ink">
                {typed}
                <span className="typing-caret" aria-hidden="true" />
              </span>
            </div>
            <p className="mx-auto mt-4 max-w-lg text-[15px] leading-relaxed text-dim lg:mx-0">
              Questions like these become real satellite radar analyses,
              drawn on a 3D globe with the numbers to back them up.
            </p>

            <div className="mt-8 flex flex-wrap items-center justify-center gap-3 lg:justify-start">
              <button
                onClick={onLaunch}
                className="group flex h-12 items-center gap-2 rounded-full bg-amber px-7 font-medium text-bg transition hover:brightness-110"
              >
                Launch Kairos
                <ArrowRight
                  size={17}
                  className="transition-transform group-hover:translate-x-0.5"
                />
              </button>
              <button
                onClick={openLiveWatch}
                className="flex h-12 items-center gap-2 rounded-full bg-surface/90 px-6 text-sm text-ink ring-1 ring-line transition-colors hover:ring-amber/60"
              >
                <Radio size={15} className="text-amber" />
                See live disasters
              </button>
              {installEvent && (
                <button
                  onClick={() => installEvent.prompt()}
                  className="flex h-12 items-center gap-2 rounded-full px-5 text-sm text-dim ring-1 ring-line transition-colors hover:text-ink"
                >
                  <Download size={15} />
                  Install app
                </button>
              )}
            </div>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 font-mono text-[11px] tracking-wider text-dim lg:justify-start">
              <span>13 ANALYSIS TYPES</span>
              <span className="text-teal">/</span>
              <span>WHOLE EARTH EVERY 12 DAYS</span>
              <span className="text-teal">/</span>
              <span>FREE ESA DATA</span>
            </div>
          </div>

          <RadarSweep />
        </div>

        <div className="relative z-10 flex justify-center pb-6">
          <ArrowDown size={16} className="animate-pulse-soft text-dim" />
        </div>
      </section>

      {findings.length > 0 && (
        <section className="border-y border-line bg-surface/40">
          <div className="mx-auto max-w-5xl px-6 py-10 sm:px-10">
            <div className="flex items-center gap-2 font-mono text-[11px] tracking-[0.25em] text-teal">
              <span className="h-1.5 w-1.5 rounded-full bg-teal animate-pulse-soft" />
              KAIROS FOUND THIS, UNPROMPTED
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              {findings.map((f) => (
                <motion.div
                  key={f.id}
                  {...reveal}
                  className="rounded-2xl bg-bg p-4 ring-1 ring-line"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full shrink-0"
                      style={{ background: ANALYSIS_COLORS[f.analysis_type] ?? "#00BFA8" }}
                    />
                    <span className="text-sm font-medium truncate">{f.region}</span>
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-dim line-clamp-3">
                    {f.summary}
                  </p>
                  <div className="mt-2 font-mono text-[10px] text-dim">
                    {f.headline_value != null &&
                      `${Math.round(f.headline_value).toLocaleString()} ${f.headline_unit} · `}
                    {timeAgo(f.created_at)}
                  </div>
                </motion.div>
              ))}
            </div>
            <p className="mt-4 text-xs text-dim">
              The system sweeps disaster zones and watchlist regions on its own
              schedule. Nobody asked it these questions.{" "}
              <button
                onClick={() => {
                  location.hash = "watch";
                  location.reload();
                }}
                className="text-teal hover:underline"
              >
                See the live feed
              </button>
            </p>
          </div>
        </section>
      )}

      <section className="mx-auto max-w-5xl px-6 py-20 sm:px-10">
        <h2 className="font-display text-2xl font-semibold sm:text-3xl">
          What you can ask it
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-dim">
          Thirteen analysis types run on the same radar archive. These are the
          ones people reach for first.
        </p>
        <div className="mt-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {CAPABILITIES.map((c, i) => (
            <motion.div
              key={c.name}
              {...reveal}
              transition={{ ...reveal.transition, delay: (i % 4) * 0.07 }}
              className="rounded-2xl bg-surface p-4 ring-1 ring-line transition-colors hover:ring-teal/40"
            >
              <c.icon size={18} className="text-teal" />
              <div className="mt-3 text-sm font-medium">{c.name}</div>
              <div className="mt-1 text-xs leading-relaxed text-dim">
                {c.blurb}
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="border-y border-line bg-surface/40">
        <div className="mx-auto max-w-5xl px-6 py-20 sm:px-10">
          <h2 className="font-display text-2xl font-semibold sm:text-3xl">
            Why radar and not photos?
          </h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <motion.div {...reveal} className="rounded-2xl bg-bg p-5 ring-1 ring-line">
              <div className="font-mono text-[10px] tracking-[0.25em] text-teal">
                CLOUDS
              </div>
              <h3 className="mt-2 font-medium">It sees through weather</h3>
              <p className="mt-2 text-xs leading-relaxed text-dim">
                Optical satellites go blind at the worst moment, because floods
                come with storms and fires come with smoke. Microwaves pass
                straight through both.
              </p>
            </motion.div>
            <motion.div
              {...reveal}
              transition={{ ...reveal.transition, delay: 0.08 }}
              className="rounded-2xl bg-bg p-5 ring-1 ring-line"
            >
              <div className="font-mono text-[10px] tracking-[0.25em] text-teal">
                DARKNESS
              </div>
              <h3 className="mt-2 font-medium">It works at night</h3>
              <p className="mt-2 text-xs leading-relaxed text-dim">
                A SAR satellite brings its own illumination. It sends a pulse
                and measures the echo, so midnight over the ocean looks the
                same as noon.
              </p>
            </motion.div>
            <motion.div
              {...reveal}
              transition={{ ...reveal.transition, delay: 0.16 }}
              className="rounded-2xl bg-bg p-5 ring-1 ring-line"
            >
              <div className="font-mono text-[10px] tracking-[0.25em] text-teal">
                ACCESS
              </div>
              <h3 className="mt-2 font-medium">It is free for everyone</h3>
              <p className="mt-2 text-xs leading-relaxed text-dim">
                Sentinel-1 data from the European Space Agency is open. Kairos
                just makes it usable without a remote-sensing degree.
              </p>
            </motion.div>
          </div>

          <p className="mt-8 max-w-3xl text-sm leading-relaxed text-dim">
            The physics in one paragraph: the satellite pings the ground with
            microwaves from 700 km up and records how much energy bounces back,
            a quantity called backscatter. Smooth open water reflects the pulse
            away like a mirror, so floods read as sudden dark patches. Buildings
            and ship hulls bounce it right back, so they read bright. Every
            analysis in Kairos is a different way of asking &ldquo;what changed
            in the echo?&rdquo;
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 py-20 sm:px-10">
        <h2 className="font-display text-2xl font-semibold sm:text-3xl">
          How a question becomes a map
        </h2>
        <ol className="mt-8 space-y-4">
          {STEPS.map((s, i) => (
            <motion.li
              {...reveal}
              transition={{ ...reveal.transition, delay: i * 0.06 }}
              key={s.title}
              className="flex gap-4 rounded-2xl bg-surface p-5 ring-1 ring-line"
            >
              <span className="font-display text-2xl font-bold text-teal/80">
                {i + 1}
              </span>
              <div>
                <h3 className="font-medium">{s.title}</h3>
                <p className="mt-1 text-xs leading-relaxed text-dim sm:text-sm">
                  {s.body}
                </p>
              </div>
            </motion.li>
          ))}
        </ol>

        <div className="mt-12 flex flex-col items-center gap-4 rounded-2xl bg-surface p-8 ring-1 ring-line text-center">
          <p className="font-display text-xl font-semibold">
            The globe is waiting.
          </p>
          <button
            onClick={onLaunch}
            className="flex h-12 items-center gap-2 rounded-full bg-amber px-7 font-medium text-bg transition hover:brightness-110"
          >
            Launch Kairos
            <ArrowRight size={17} />
          </button>
        </div>
      </section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-5xl flex-col gap-2 px-6 py-8 text-xs text-dim sm:px-10">
          <span>Built by students for the Congressional App Challenge.</span>
          <span>
            Data: Sentinel-1, ESA Copernicus. Processing: Google Earth Engine.
            Basemap: Mapbox.
          </span>
        </div>
      </footer>
    </div>
    </MotionConfig>
  );
}
