import { useState } from "react";
import {
  ArrowLeft,
  Award,
  BookOpen,
  ExternalLink,
  Newspaper,
  Check,
  ChevronRight,
  GraduationCap,
  Lightbulb,
  Moon,
  Radar,
  RefreshCw,
  Satellite,
  ShieldQuestion,
  Waves,
  X,
} from "lucide-react";
import { goToApp } from "../../lib/embed";
import { buildShareUrl } from "../../lib/share";
import { CASE_STUDIES } from "../../lib/caseStudies";

interface Lesson {
  icon: typeof Radar;
  chip: string;
  title: string;
  body: string[];
  key: string;
}

const LESSONS: Lesson[] = [
  {
    icon: Moon,
    chip: "The trick",
    title: "A camera that brings its own light",
    key: "Radar is active: it makes its own illumination.",
    body: [
      "A normal satellite camera works like your eyes. It needs sunlight, and a single cloud blocks the view. Half the Earth is dark at any moment and about two thirds is under cloud, so optical satellites miss most of what happens.",
      "Radar satellites cheat. They send their own radio pulse down at the ground and time the echo that comes back. No sun needed, and radio waves pass straight through clouds, smoke and rain. That is why every image in Kairos works at midnight in a monsoon.",
      "This technique is called SAR, synthetic aperture radar. The 'synthetic aperture' part is a trick where the satellite uses its own motion to act like an antenna hundreds of meters long, which is what makes the images sharp.",
    ],
  },
  {
    icon: Waves,
    chip: "The one rule",
    title: "Rough is bright, smooth is dark",
    key: "Surface texture, not color, is what radar sees.",
    body: [
      "Radar does not see color at all. It sees texture. A rough surface, like a forest canopy or choppy sea, scatters the radio pulse in every direction, and some of it bounces back to the satellite. That pixel reads bright.",
      "A smooth surface, like calm water or fresh asphalt, works like a mirror: the pulse bounces away from the satellite and almost nothing returns. That pixel reads dark.",
      "This one rule explains nearly everything Kairos detects. Flooded fields turn dark because water is smooth. Ships are bright metal spikes on a dark sea. Oil flattens ripples, so slicks are extra-dark stripes. A clear-cut forest gets darker because a rough canopy became bare ground.",
    ],
  },
  {
    icon: Satellite,
    chip: "The satellite",
    title: "Meet Sentinel-1",
    key: "Free, public radar coverage of the whole planet.",
    body: [
      "Kairos runs on Sentinel-1, a radar satellite operated by the European Space Agency about 700 km up. It circles the Earth pole to pole every 99 minutes and images the same spot roughly every 12 days.",
      "Its radar works at a 5.5 cm wavelength (C-band). That number matters: waves that size bounce off things bigger than a few centimeters, like leaves, waves, walls, so it reads surface texture at exactly the scale where floods, ships and clearings show up.",
      "Every image is free and public. Anyone can check any claim Kairos makes against the same archive, which is exactly how we want it.",
    ],
  },
  {
    icon: Radar,
    chip: "The method",
    title: "How Kairos finds change",
    key: "Compare after against before, keep only real differences.",
    body: [
      "One radar image is hard to read. Two are easy. Kairos builds a 'before' picture by averaging passes from the weeks before your dates, then compares the 'after' images against it, pixel by pixel.",
      "A pixel that dropped more than 3 decibels darker than its own baseline probably went from dry land to standing water. One that jumped brighter in a city after an earthquake is rubble and tilted walls. Each of the nineteen analyses is one of these physical rules.",
      "Kairos then removes known distractions, like rivers and lakes that were always there (a 40-year water map handles that), and turns what is left into the area numbers and overlays you see.",
    ],
  },
  {
    icon: ShieldQuestion,
    chip: "The honesty part",
    title: "When radar lies, and how we catch it",
    key: "Every detection has failure modes; test them, do not hide them.",
    body: [
      "Radar has classic false positives. Rain-soaked farmland darkens like a flood. A windless day flattens the sea like an oil slick. A harvested field looks like a fresh clearing.",
      "Kairos does two things about this. Every result carries a confidence score and an explainer that names the ways it could be wrong. And the 'Test other explanations' button actually pulls the rainfall, wind and land-cover records for your exact area and dates to check whether an innocent explanation fits.",
      "There is also a measured accuracy page: Kairos re-runs its detectors over historical disasters where independent reference maps exist and reports the overlap. Real numbers, computed live, not marketing.",
    ],
  },
];

interface Question {
  q: string;
  options: string[];
  answer: number;
  why: string;
}

const QUIZ: Question[] = [
  {
    q: "Why can Sentinel-1 take images at midnight?",
    options: [
      "Its sensors amplify starlight",
      "It sends its own radio pulse and times the echo",
      "It stores daytime images and replays them",
    ],
    answer: 1,
    why: "Radar is active. It illuminates the ground itself, so it never needs the sun.",
  },
  {
    q: "What happens when the radar pulse hits a thick storm cloud?",
    options: [
      "It mostly passes straight through",
      "It reflects back early and ruins the image",
      "It gets absorbed and the image goes black",
    ],
    answer: 0,
    why: "At a 5.5 cm wavelength, cloud droplets are far too small to block the wave. That is the whole advantage over normal cameras.",
  },
  {
    q: "Calm water in a radar image looks...",
    options: ["Bright white", "Almost black", "Blue"],
    answer: 1,
    why: "A smooth surface acts like a mirror and bounces the pulse away from the satellite, so almost no echo returns. Radar sees texture, never color.",
  },
  {
    q: "How does Kairos spot a new flood?",
    options: [
      "Pixels that turned much darker than their own past average",
      "Pixels that turned blue",
      "Pixels that got warmer",
    ],
    answer: 0,
    why: "Land that goes underwater becomes smooth, so its echo drops. Kairos flags pixels more than 3 dB darker than their pre-flood baseline.",
  },
  {
    q: "Why are ships easy to find at sea?",
    options: [
      "They leave a warm wake",
      "Metal corners bounce the pulse straight back, making bright spots on a dark sea",
      "Their GPS transponders show in the image",
    ],
    answer: 1,
    why: "A ship's right-angled metal surfaces act like a mirror aimed back at the satellite. One bright pixel cluster on smooth dark water is hard to miss.",
  },
  {
    q: "About how often does Sentinel-1 revisit the same spot?",
    options: ["Every 90 minutes", "Every 12 days", "Once a year"],
    answer: 1,
    why: "It orbits every 99 minutes but images a narrow strip each pass; covering the same ground again takes about 12 days.",
  },
  {
    q: "An oil slick shows up as...",
    options: [
      "A rainbow-colored patch",
      "A dark stripe, because oil flattens the small waves",
      "A bright stripe, because oil is shiny",
    ],
    answer: 1,
    why: "Oil damps the centimeter-scale ripples that normally scatter energy back. Flat sea means dark pixels.",
  },
  {
    q: "Which of these can fool a radar flood detector?",
    options: [
      "Heavy rain soaking farmland just before the pass",
      "A full moon",
      "Cold weather",
    ],
    answer: 0,
    why: "Wet soil darkens like shallow water does. That is why Kairos pulls the actual rainfall record and warns you when this explanation is live.",
  },
  {
    q: "What does 'backscatter' mean?",
    options: [
      "Radio interference from cities",
      "The part of the radar pulse that bounces back to the satellite",
      "The satellite's exhaust trail",
    ],
    answer: 1,
    why: "Every Kairos analysis is a rule about how backscatter changes: floods drop it, rubble raises it, clearings drop it in the cross-polarized channel.",
  },
  {
    q: "How much does a Sentinel-1 image cost you?",
    options: ["About $500", "About $50", "Nothing"],
    answer: 2,
    why: "ESA publishes the entire archive for free. Kairos is built to prove anyone, including a student, can turn it into answers.",
  },
];

type Tab = "learn" | "cases" | "quiz";

export default function Academy() {
  const [tab, setTab] = useState<Tab>("learn");
  const [lesson, setLesson] = useState(0);
  const [openCase, setOpenCase] = useState<string | null>(CASE_STUDIES[0].id);
  const [qIndex, setQIndex] = useState(0);
  const [picked, setPicked] = useState<number | null>(null);
  const [score, setScore] = useState(0);
  const [finished, setFinished] = useState(false);

  const L = LESSONS[lesson];
  const Q = QUIZ[qIndex];

  function pick(i: number) {
    if (picked !== null) return;
    setPicked(i);
    if (i === Q.answer) setScore((s) => s + 1);
  }

  function nextQuestion() {
    if (qIndex === QUIZ.length - 1) {
      setFinished(true);
    } else {
      setQIndex((i) => i + 1);
      setPicked(null);
    }
  }

  function restart() {
    setQIndex(0);
    setPicked(null);
    setScore(0);
    setFinished(false);
  }

  return (
    <div className="h-full w-full bg-bg overflow-y-auto">
      <header className="sticky top-0 z-40 flex items-center justify-between px-4 sm:px-6 h-14 bg-bg/80 backdrop-blur border-b border-line">
        <div className="flex items-center gap-3">
          <button
            onClick={goToApp}
            className="flex items-center gap-1.5 text-dim hover:text-ink transition-colors text-xs"
          >
            <ArrowLeft size={14} /> App
          </button>
          <span className="hidden sm:inline font-mono text-[10px] tracking-[0.24em] text-dim">
            KAIROS <span className="text-teal">ACADEMY</span>
          </span>
        </div>
        <div className="flex items-center gap-1 rounded-xl ring-1 ring-line p-0.5 shrink-0">
          <button
            onClick={() => setTab("learn")}
            className={`h-8 px-2.5 sm:px-3 rounded-[10px] text-xs flex items-center gap-1.5 transition ${
              tab === "learn" ? "bg-raised text-ink" : "text-dim hover:text-ink"
            }`}
          >
            <BookOpen size={13} /> Learn
          </button>
          <button
            onClick={() => setTab("cases")}
            className={`h-8 px-2.5 sm:px-3 rounded-[10px] text-xs flex items-center gap-1.5 transition ${
              tab === "cases" ? "bg-raised text-ink" : "text-dim hover:text-ink"
            }`}
          >
            <Newspaper size={13} /> Cases
          </button>
          <button
            onClick={() => setTab("quiz")}
            className={`h-8 px-2.5 sm:px-3 rounded-[10px] text-xs flex items-center gap-1.5 transition ${
              tab === "quiz" ? "bg-raised text-ink" : "text-dim hover:text-ink"
            }`}
          >
            <GraduationCap size={13} /> Quiz
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        {tab === "learn" ? (
          <div className="space-y-5">
            <div className="flex flex-wrap gap-1.5">
              {LESSONS.map((l, i) => (
                <button
                  key={i}
                  onClick={() => setLesson(i)}
                  className={`h-8 px-3 rounded-full text-[11px] ring-1 transition ${
                    i === lesson
                      ? "bg-raised ring-teal/50 text-teal"
                      : "ring-line text-dim hover:text-ink"
                  }`}
                >
                  {i + 1}. {l.chip}
                </button>
              ))}
            </div>

            <div className="rounded-2xl bg-surface ring-1 ring-line p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className="h-11 w-11 grid place-items-center rounded-2xl bg-raised ring-1 ring-teal/30 text-teal">
                  <L.icon size={20} />
                </div>
                <div>
                  <div className="font-mono text-[9px] tracking-[0.2em] text-amber uppercase">
                    Lesson {lesson + 1} of {LESSONS.length}
                  </div>
                  <h1 className="font-display text-xl text-ink leading-tight mt-0.5">
                    {L.title}
                  </h1>
                </div>
              </div>

              {L.body.map((p, i) => (
                <p key={i} className="text-sm text-dim leading-relaxed">
                  {p}
                </p>
              ))}

              <div className="rounded-xl bg-bg/60 ring-1 ring-line px-3 py-2.5 flex items-start gap-2">
                <Lightbulb size={13} className="text-teal shrink-0 mt-0.5" />
                <span className="text-[11px] text-teal/90 leading-snug">
                  Remember one thing: {L.key}
                </span>
              </div>

              <div className="flex justify-between pt-1">
                <button
                  onClick={() => setLesson((i) => Math.max(0, i - 1))}
                  disabled={lesson === 0}
                  className="h-9 px-4 rounded-xl ring-1 ring-line text-xs text-dim hover:text-ink transition disabled:opacity-30"
                >
                  Back
                </button>
                {lesson < LESSONS.length - 1 ? (
                  <button
                    onClick={() => setLesson((i) => i + 1)}
                    className="h-9 px-4 rounded-xl bg-amber text-bg text-xs font-medium hover:brightness-110 transition flex items-center gap-1"
                  >
                    Next lesson <ChevronRight size={13} />
                  </button>
                ) : (
                  <button
                    onClick={() => setTab("quiz")}
                    className="h-9 px-4 rounded-xl bg-amber text-bg text-xs font-medium hover:brightness-110 transition flex items-center gap-1"
                  >
                    Take the quiz <GraduationCap size={13} />
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : tab === "cases" ? (
          <div className="space-y-4">
            <div>
              <h1 className="font-display text-xl text-ink">
                Three times radar was the only thing watching
              </h1>
              <p className="mt-2 text-sm text-dim leading-relaxed">
                Real events, real dates. Read what happened, then run the same
                analysis Kairos would have run at the time and see the data for
                yourself.
              </p>
            </div>
            {CASE_STUDIES.map((c) => {
              const open = openCase === c.id;
              return (
                <div
                  key={c.id}
                  className="rounded-2xl bg-surface ring-1 ring-line overflow-hidden"
                >
                  <button
                    onClick={() => setOpenCase(open ? null : c.id)}
                    className="w-full px-5 py-4 text-left"
                  >
                    <div className="font-mono text-[9px] tracking-[0.2em] text-amber uppercase">
                      {c.place} · {c.when}
                    </div>
                    <div className="mt-1 font-display text-lg text-ink leading-snug">
                      {c.title}
                    </div>
                    <p className="mt-1.5 text-xs text-dim leading-relaxed">
                      {c.hook}
                    </p>
                  </button>
                  {open && (
                    <div className="px-5 pb-5 space-y-3">
                      {c.story.map((p, i) => (
                        <p key={i} className="text-sm text-dim leading-relaxed">
                          {p}
                        </p>
                      ))}
                      <div className="rounded-xl bg-bg/60 ring-1 ring-line p-3">
                        <div className="font-mono text-[9px] tracking-[0.2em] text-teal uppercase">
                          What the radar saw
                        </div>
                        <p className="mt-1 text-[12px] text-dim leading-relaxed">
                          {c.whatRadarSaw}
                        </p>
                      </div>
                      <a
                        href={buildShareUrl({
                          analysis_type: c.analysis_type,
                          bbox: c.bbox,
                          start_date: c.start_date,
                          end_date: c.end_date,
                        })}
                        className="flex h-10 items-center justify-center gap-2 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition"
                      >
                        {c.runLabel} <ExternalLink size={13} />
                      </a>
                      <p className="text-[11px] text-amber/90 leading-snug">
                        {c.caution}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : finished ? (
          <div className="rounded-2xl bg-surface ring-1 ring-line p-8 text-center space-y-4">
            <Award size={36} className="mx-auto text-amber" />
            <h1 className="font-display text-2xl text-ink">
              {score} / {QUIZ.length}
            </h1>
            <p className="text-sm text-dim leading-relaxed">
              {score === QUIZ.length
                ? "Perfect. You now read radar images better than most adults."
                : score >= 7
                ? "Strong. You have the core physics down; skim the lessons for the ones you missed."
                : "Good start. The lessons cover every answer, two minutes each."}
            </p>
            <div className="flex justify-center gap-2">
              <button
                onClick={restart}
                className="h-10 px-4 rounded-xl ring-1 ring-line text-xs text-ink hover:ring-teal/50 transition flex items-center gap-1.5"
              >
                <RefreshCw size={13} /> Try again
              </button>
              <button
                onClick={goToApp}
                className="h-10 px-4 rounded-xl bg-amber text-bg text-xs font-medium hover:brightness-110 transition"
              >
                Use the real thing
              </button>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl bg-surface ring-1 ring-line p-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[9px] tracking-[0.2em] text-amber uppercase">
                Question {qIndex + 1} of {QUIZ.length}
              </span>
              <span className="font-mono text-[9px] text-dim">
                score {score}
              </span>
            </div>
            <h1 className="font-display text-lg text-ink leading-snug">
              {Q.q}
            </h1>
            <div className="space-y-2">
              {Q.options.map((opt, i) => {
                const isPicked = picked === i;
                const isRight = i === Q.answer;
                const show = picked !== null;
                return (
                  <button
                    key={i}
                    onClick={() => pick(i)}
                    disabled={picked !== null}
                    className={`w-full flex items-center gap-2.5 rounded-xl ring-1 px-3.5 py-3 text-left text-sm transition ${
                      show && isRight
                        ? "bg-raised ring-teal/60 text-teal"
                        : show && isPicked
                        ? "bg-bg/70 ring-amber/60 text-amber"
                        : "bg-bg/70 ring-line text-ink hover:ring-teal/40"
                    }`}
                  >
                    {show && isRight ? (
                      <Check size={14} className="shrink-0" />
                    ) : show && isPicked ? (
                      <X size={14} className="shrink-0" />
                    ) : (
                      <span className="h-3.5 w-3.5 rounded-full ring-1 ring-line shrink-0" />
                    )}
                    {opt}
                  </button>
                );
              })}
            </div>
            {picked !== null && (
              <>
                <p className="text-[12px] text-dim leading-relaxed rounded-xl bg-bg/60 ring-1 ring-line px-3 py-2.5">
                  {Q.why}
                </p>
                <button
                  onClick={nextQuestion}
                  className="w-full h-10 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition"
                >
                  {qIndex === QUIZ.length - 1 ? "See my score" : "Next question"}
                </button>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
