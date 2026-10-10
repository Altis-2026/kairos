import { ArrowLeft, Github, Satellite } from "lucide-react";
import KairosMark from "../KairosMark";
import { navigate } from "../../lib/navigation";

const BUILDERS = [
  { name: "Prem Kamasani", role: "Co-founder" },
  { name: "Amogh Vinaykumar", role: "Co-founder" },
];

const DATA = [
  ["Sentinel-1 radar", "European Space Agency, Copernicus programme"],
  ["Sentinel-2 optical, Sentinel-5P atmosphere", "European Space Agency, Copernicus programme"],
  ["Landsat 8 and 9 thermal", "NASA and USGS"],
  ["Copernicus GLO-30 elevation", "European Space Agency"],
  ["Global Surface Water", "European Commission Joint Research Centre"],
  ["Population and built-up area (GHSL)", "European Commission Joint Research Centre"],
  ["ESA WorldCover land cover", "European Space Agency"],
  ["CHIRPS rainfall, ERA5 wind", "UC Santa Barbara Climate Hazards Center, ECMWF"],
  [
    "Global Flood Database, MODIS burned area, Hansen forest change",
    "Cloud to Street, NASA, University of Maryland",
  ],
  ["Active disaster events (EONET)", "NASA Earth Observatory"],
  ["Congressional district boundaries (TIGERweb)", "US Census Bureau"],
  ["Ship transponder broadcasts (AIS)", "NOAA and BOEM MarineCadastre"],
  ["Processing", "Google Earth Engine"],
  ["Basemaps and geocoding", "Mapbox"],
];

const LIBRARIES = [
  "React",
  "TypeScript",
  "Vite",
  "Mapbox GL JS",
  "Zustand",
  "TanStack Query",
  "Tailwind CSS",
  "Framer Motion",
  "Lucide icons",
  "Firebase",
  "FastAPI",
  "Pydantic",
  "Earth Engine Python API",
  "NumPy",
  "HTTPX",
  "OpenAI Python SDK (for OpenRouter)",
  "Redis and RQ",
  "pytest",
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-10">
      <h2 className="font-mono text-[11px] tracking-[0.22em] text-amber uppercase">{title}</h2>
      <div className="mt-3 text-sm text-ink/90 leading-relaxed space-y-3">{children}</div>
    </section>
  );
}

export default function About() {
  return (
    <main className="min-h-full w-full overflow-y-auto bg-bg text-ink">
      <div className="mx-auto max-w-3xl px-5 py-8 sm:py-12">
        <button
          onClick={() => navigate("app")}
          className="inline-flex items-center gap-2 text-sm text-dim hover:text-ink transition"
        >
          <ArrowLeft size={15} /> Back to the globe
        </button>

        <header className="mt-8 flex items-center gap-4">
          <span className="h-14 w-14 grid place-items-center rounded-2xl bg-surface ring-1 ring-line text-[#C9E6F7]">
            <KairosMark size={36} title="Kairos" />
          </span>
          <div>
            <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight">About Kairos</h1>
            <p className="mt-1 text-dim">Satellite radar for everyone.</p>
          </div>
        </header>

        <p className="mt-8 text-base sm:text-lg leading-relaxed text-ink/90">
          Kairos turns a plain-language question into a real measurement from space. It reads free radar data
          from Europe's Sentinel-1 satellites, which see through clouds, smoke and darkness, and explains what
          it found in words anyone can follow. It also simulates floods and wildfires on real terrain, and
          helps families, local leaders and students prepare for what comes next.
        </p>

        <Section title="Built by">
          <div className="grid sm:grid-cols-2 gap-3">
            {BUILDERS.map((b) => (
              <div key={b.name} className="rounded-2xl bg-surface ring-1 ring-line p-4">
                <div className="font-display text-lg">{b.name}</div>
                <div className="text-xs text-dim">{b.role} · Flower Mound High School, Texas</div>
              </div>
            ))}
          </div>
          <p className="text-dim">
            Kairos is part of Altis, alongside our other projects. It is free to use, has no ads, and needs no
            account.
          </p>
        </Section>

        <Section title="Why we built it">
          <p>
            In July 2025 the Guadalupe River rose about 26 feet in under an hour and more than 135 people died
            in the Texas Hill Country floods, a few hours from where we live. The storm that caused the
            flooding also hid it from camera satellites. Radar data that could see through those clouds was
            sitting in a free public archive, but reading it took specialist software and training. Kairos is
            our attempt to fix that.
          </p>
        </Section>

        <Section title="How AI is used">
          <p>
            Every number Kairos shows comes from deterministic computations on real satellite data in Google
            Earth Engine, or from our own flood and wildfire physics models. AI never produces a measurement.
          </p>
          <p>
            A language model (through OpenRouter) turns typed or spoken questions into analysis settings and
            writes the plain-language explanations of finished results. The Janus research mentor uses the
            same models to plan studies and call Kairos's tools. The analysis wizard, featured stories,
            simulations and every map tool work without it. Our README has the full disclosure of how AI was
            used while building Kairos.
          </p>
        </Section>

        <Section title="Data and credit">
          <ul className="divide-y divide-line rounded-2xl bg-surface ring-1 ring-line">
            {DATA.map(([what, who]) => (
              <li key={what} className="flex flex-col sm:flex-row sm:justify-between gap-1 px-4 py-2.5">
                <span>{what}</span>
                <span className="text-dim text-xs sm:text-sm sm:text-right">{who}</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-dim">
            Contains modified Copernicus Sentinel data, processed on Google Earth Engine.
          </p>
        </Section>

        <Section title="Open-source libraries">
          <p className="text-dim">
            Kairos is built on these open-source projects. Thank you to their maintainers.
          </p>
          <div className="flex flex-wrap gap-2">
            {LIBRARIES.map((l) => (
              <span
                key={l}
                className="px-3 py-1 rounded-full bg-surface ring-1 ring-line text-xs text-ink/80"
              >
                {l}
              </span>
            ))}
          </div>
        </Section>

        <footer className="mt-12 flex flex-wrap items-center gap-4 border-t border-line pt-6 text-sm text-dim">
          <a
            href="https://github.com/Altis-2026/kairos"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 hover:text-ink transition"
          >
            <Github size={15} /> Source code
          </a>
          <span className="inline-flex items-center gap-2">
            <Satellite size={15} className="text-teal" /> MIT licensed
          </span>
        </footer>
      </div>
    </main>
  );
}
