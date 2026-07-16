# Janus: the satellite research mentor

The plan of record for Kairos's second product. Janus is to satellite/Earth
observation research what Scoriel is to bioinformatics: an AI mentor that
teaches you how to do real research and then works alongside you like a PhD
scientist while you do it, using Kairos as the instrument.

Named for the two-faced god: one face toward the student learning the craft,
one toward the researcher producing new knowledge.

---

## 1. What Janus is (and is not)

**Is:** a mentor. It teaches skills, questions your reasoning, reviews your
work, and points you in the right direction. You do the research. That framing
matters pedagogically (people learn), legally (your paper is yours), and
commercially (mentorship justifies a subscription; a one-shot answer machine
does not).

**Is not:** a paper mill. Janus does not ghost-write manuscripts or fabricate
figures end-to-end. It will critique your figure, not fake one.

**The one-line pitch:** "Bring Janus any question about the Earth. It will
teach you how a scientist would answer it, then work with you until you have."

## 2. Who it's for

1. **Students** (high school through grad school) doing science-fair,
   thesis, or first-paper research with satellite data. Largest pool,
   cheapest tier, most word-of-mouth.
2. **Researchers in adjacent fields** (economics, epidemiology, archaeology,
   journalism, insurance, conservation) who need EO evidence but lack the
   remote-sensing training. Highest willingness to pay.
3. **NGO / government analysts** who use Kairos operationally and need to
   defend findings ("how confident are we in this flood extent?"). Natural
   team-plan buyers.

## 3. What Janus can do, by version

### v1 — the mentor in the app (waitlist launch)
- **Research tutor:** structured curricula ("SAR fundamentals in 5 sessions",
  "from question to study design"), taught conversationally inside Kairos,
  each lesson ending in a live exercise run on real Sentinel-1 data.
- **Study designer:** turns a vague interest ("I think mining is polluting my
  river") into a testable design: hypothesis, AOI, time windows, analysis
  types, confounders, and the validation plan, then executes it with the
  user via the existing Kairos tools.
- **Literature companion:** finds and summarizes relevant papers (OpenAlex +
  arXiv + Semantic Scholar APIs), explains methods sections in plain
  language, and keeps a running annotated bibliography per project.
- **Dataset scout:** knows the GEE catalog, the Copernicus/STAC ecosystem,
  and Kairos's own registry; recommends the right data for a question,
  including its limits ("GRD amplitude cannot give you millimetre
  subsidence; here is what can").
- **Methods critic:** reviews the user's reasoning and outputs. "Your
  baseline window overlaps the previous flood." "Your AOI is 80% rice paddy;
  NDWI will confuse you." Powered by the same honesty layer the interpreter
  already ships (proxies, false positives, uncertainty ranges).
- **Project memory:** each research project is a persistent thread: question,
  design, runs, readings, drafts, critiques. Resumable for months.

### v2 — the researcher's power tools + the "feels alive" layer

**SHIPPED (backend/janus/ + the panel):**
- **Reproducibility pack** (`reproducibility.py`, `GET /janus/projects/{id}/pack`):
  one click exports a project's full method trail as a Markdown research
  pack — question, study design, every analysis run with its exact
  parameters and imagery date, ground-truth validation results, the
  annotated bibliography, reproducible Kairos case links, and an honest
  limitations footer. Everything is reconstructed from stored tool events,
  so it cannot claim a run that did not happen.
- **Proactive monitoring** (`proactive.py`, the Watch toggle): a project can
  be put on WATCH. On a schedule (and instantly when toggled on), Janus
  checks for a fresh Sentinel-1 pass over the study area since the last
  analysis and, when one lands, surfaces an insight banner — "Janus noticed
  a new pass on <date>, want me to re-run and compare?" — with a one-click
  re-run. This is the highest-leverage "feels like a real AI" upgrade:
  Janus acts without being prompted. Deliberately cheap (scene-date checks,
  not full analyses) and opt-in.
- **Voice mode** (`lib/voice.ts`): push-to-talk dictation and read-aloud
  replies, built on the browser Web Speech API, so it costs nothing and
  needs no API key. Everything spoken still lands in the project's text
  history for search and citation. (Premium neural TTS — ElevenLabs / OpenAI
  TTS — is the documented upgrade path; the client-side version is the
  zero-cost foundation.)
- **Entitlements / paid gating** (`entitlements.py`, `GET /janus/entitlements`):
  the tier → feature map is real and enforced today (project caps, feature
  gates return HTTP 402). The default tier is a generous "early access" that
  unlocks everything free, so the launch feels unlimited while the gates
  quietly exist, ready for Stripe.
- **Validation coach:** the mentor's `run_ground_truth_validation` tool +
  review mode already teach IoU/precision/recall against the benchmark suite.

### v3 — the research power tools (SHIPPED)

The layer that pushes Janus from "a mentor" toward "can almost do anything"
for satellite research. All in `backend/janus/*`, `backend/gee/confounders.py`,
and the panel.

- **Automated confounder analysis** (`gee/confounders.py`, `check_confounders`
  tool): the honest-radar ethos made computational. After a detection, Janus
  pulls the real environmental variables that drive each false positive —
  CHIRPS rainfall, ERA5 wind, ESA WorldCover land cover — for the exact AOI
  and dates, and judges whether a confounder is plausibly in play ("48 mm of
  rain fell in the 5 days before your flood window", "wind was 2 m/s, calm
  enough to mimic an oil slick without oil"). It TESTS the confounders it used
  to only warn about.
- **Reproducible code export** (`notebook.py`, `GET .../notebook`): emits a
  runnable Python earthengine-api script that reproduces every analysis in the
  project from scratch. A researcher pastes it into Colab, authenticates their
  own EE account, and gets the same maps and numbers independently of Kairos —
  the strongest form of "show your work".
- **Research log / hypothesis tracker** (`hypotheses` table, `log_hypothesis`
  / `update_hypothesis` tools): structured hypotheses with an evolving status
  (open → supported / refuted / inconclusive) and the evidence tied to each.
  The chat becomes a real research notebook; it feeds the pack and the review.
- **Peer-review report** (`review_report.py`, `GET .../review`): a formal
  mock-reviewer assessment of the WHOLE project against a fixed rubric
  (summary, strengths, threats to validity, required/suggested revisions, a
  verdict), generated from the facts on record and downloadable. Students
  pressure-test their work before a human sees it. Deterministic checklist
  fallback when no AI provider is set.
- **Adaptive skills memory** (`skills` table, `record_skill` tool): a
  per-student skills profile that persists across ALL their projects, injected
  into every mentor turn so Janus teaches to the gaps and genuinely remembers
  who it's working with — the "it knows me" upgrade.

### v4 — beyond SAR, and hands-off autopilot (SHIPPED)

The layer that makes Janus useful to people who don't care about radar at all,
and lets a user just describe a goal and have it carried out.

- **Multi-sensor expansion (3 new analyses):** the platform is no longer
  radar-only. `forest_biomass` fuses ALOS PALSAR L-band radar (which
  penetrates canopy, unlike Sentinel-1's C-band) with Sentinel-2 NDVI for an
  above-ground-biomass estimate — a genuine two-sensor fusion. `methane` and
  `air_quality` map Sentinel-5P/TROPOMI CH4 and NO2 columns, a completely
  different modality (atmospheric composition) that opens climate and
  pollution research. All three are ordinary registry entries, so they flow
  through the sidebar, the chat, and every Janus tool automatically.
- **Autopilot mode:** the student describes a goal in one message ("check if
  there was flooding near Dhaka last month and whether it's real") and Janus
  runs the whole investigation autonomously — pick analysis, check coverage,
  run it, test confounders, validate if a benchmark fits, log the hypothesis,
  and report an honest verdict — narrating each step. Larger tool budget (14
  rounds), Sonnet-tier reasoning, gated to paid tiers (compute-heavy). Pairs
  naturally with voice: describe it out loud, hear it work.
- **Systematic literature review** (`literature.systematic_review`,
  `literature_review` tool): multiple search angles pooled, deduped and ranked
  by citation impact, with a year-span summary the mentor synthesizes into a
  "what's been done / where's the gap" narrative — still citing only real
  returned papers.
- **Citation formatting** (`citations.py`, `format_citations` tool +
  `GET .../citations`): the bibliography as a paste-ready reference list in
  APA, AGU or IEEE.
- **ARSET-modeled curricula:** two new teaching tracks — "Air Quality from
  Space" and "Forests and Carbon" — modeled on NASA ARSET's real training
  themes, each teaching the new data with live exercises.
- **Earthdata plumbing** (`gee/earthdata.py`): reads `EARTHDATA_TOKEN` from the
  environment (never hardcoded) and reports InSAR-readiness. The credential
  path for future Sentinel-1 SLC / InSAR is wired; the interferometric
  processor on dedicated compute remains the separate infrastructure build.

### v5 — close the loop into a real deliverable (SHIPPED)
The output no longer stops one step short of "paste into your actual paper."

- **Publication figures from results, not just tile URLs** (`janus/figures.py`).
  Every project renders paper-ready figures straight from its stored runs:
  a **results chart** (headline metric per analysis, with uncertainty whiskers;
  bars are scaled *within* each unit and only share a numeric axis when every
  run shares one unit, so magnitudes are never compared dishonestly), a
  **study-area map** (the AOI drawn to scale with lon/lat ticks, a km scale bar,
  extent/area facts, and a global locator), and a **validation chart**
  (IoU / precision / recall / F1 per benchmark). All emitted as standalone
  **SVG** — vector, zero plotting dependency, identical in dev and on Cloud Run,
  and drops into LaTeX (`\includesvg`), Google Docs, and HTML. Previewed inline
  in the Janus panel and downloadable per figure.
  `GET /janus/projects/{id}/figures`, `GET …/figure/{kind}`.
- **Finish in the tools researchers actually use** (`janus/exports.py`):
  - **LaTeX / Overleaf** — a complete, compilable `.tex` manuscript (title,
    question, study design, methods, a results table + figures, validation,
    honest limitations, and a `thebibliography`). `GET …/latex`.
  - **Zotero / Mendeley / EndNote** — the bibliography as **BibTeX** (`.bib`)
    and **RIS** (`.ris`), with author strings parsed for both the literature
    pipeline's "First Last, First Last" and hand-entered "Last, First and …".
    `GET …/bibtex`, `GET …/ris`.
  - **Google Docs** — a clean, self-contained HTML document whose headings map
    onto Docs styles, so File → Open lands a structured doc. `GET …/gdoc`.
  All export/figure endpoints reuse the existing ownership check and the
  `reproducibility_pack` entitlement.

### v6 — the moat (next)
- **True InSAR:** a compute backend (SNAP/ISCE on Cloud Batch) pulling SLC
  from ASF with the Earthdata token — the one item that needs real
  infrastructure spend, not just a key.
- **Cohorts and classrooms:** teacher dashboards, assignment templates,
  team projects (school license revenue).
- **Janus-reviewed public gallery:** finished student projects published with
  reproducible links; the marketing engine and the credibility engine.
- **Proactive push notifications** and premium neural voice.
- **Custom pipelines:** guided authoring of new analysis recipes saved to the
  user's account, riding on the AnalysisRegistry pattern.

## 4. Architecture

Deliberately thin on top of what already exists:

- **Model:** Claude via the existing OpenRouter client (`ai/client.py`).
  Haiku 4.5 for chat/tutoring turns; escalate to Sonnet for study-design and
  review turns (the expensive, high-stakes reasoning). Same key, same client,
  per-turn model choice.
- **Tools (function calls):** run_analysis (exists), scenes/registry
  (exists), validation/run (exists), impact stats (exists), literature
  search (new, thin wrappers over OpenAlex/arXiv/Semantic Scholar REST),
  GEE catalog search (new, static index shipped with the backend).
- **Mentor state:** a `janus_projects` table (Postgres or Firestore):
  project, goal, curriculum position, bibliography, run history, critique
  log. This is the only genuinely new backend surface.
- **Frontend:** a Janus panel in the existing app shell (same design
  system), plus a project view. The chat bar already exists; Janus is a mode
  of it, not a second app.
- **Voice (v2):** browser mic capture streamed to a speech-to-text API
  (OpenAI Whisper or Deepgram, picked at build time on latency/cost), text
  goes through the same mentor pipeline and tool calls as typed chat so
  there is no separate "voice brain," and the reply is spoken back with a
  low-latency TTS API (ElevenLabs or OpenAI TTS). Turn-taking and interrupt
  handling are the hard part, not the model call, so this gets its own spike
  before being scoped into a release. Priced into the Researcher tier only
  at first, since STT/TTS cost per minute dwarfs a text turn's token cost.
- **System prompt:** a mentor persona with hard rules: never fabricate a
  citation, never state a detection as ground truth, always name the
  false-positive modes, push the student to answer before answering.

## 5. Paid plan

- **Free (Kairos):** the globe, all 13 analyses, Live Watch, Guardian,
  sharing. Stays free; it is the top of the funnel and the public good.
- **Janus Student — $15/mo (or $10 with .edu):** full mentor, 3 active
  projects, standard model tier.
- **Janus Researcher — $49/mo:** unlimited projects, Sonnet-tier reasoning
  everywhere, reproducibility packs, validation coach, priority compute.
- **Teams / classrooms — $199/mo:** 30 seats, teacher dashboard, shared
  projects.
- **Positioning:** price against tutoring and coursework tools (Chegg,
  Brilliant, a single hour of human tutoring), not against ChatGPT.
  The pitch is "a research advisor for the price of one pizza a month."
- **Cost sanity:** a heavy Janus user might burn a few dollars of model
  spend per month at Haiku prices; margins survive even at $15.

## 6. Launch sequence

0. **SHIPPED — v1 mentor loop is live in the app** (`backend/janus/*`,
   `api/janus.py`, the telescope panel in the frontend): persistent
   projects, both curricula, study designer with saved designs, literature
   companion (OpenAlex, real citations only), dataset scout, methods
   critic (review mode), and live tool calls into run_analysis /
   scene preview / ground-truth validation / human impact. Free while in
   early access; per-turn model routing (Haiku for tutoring, Sonnet for
   design/review) already in place.
1. **Now:** waitlist live on the landing page (`/waitlist`, shipped) with
   the three-pillar teaser. Every signup logged durably.
2. **Waitlist warm-up:** short demo clips (30-60s: "Janus designs a flood
   study from one sentence") posted publicly; the Scoriel playbook of
   building in public with a running waitlist count.
3. **Alpha (first 20-50 from waitlist, free):** v1 scope only. Success
   metric: one user finishes a real project end to end and says the mentor,
   not the map, was the value.
4. **Beta + payments:** Stripe, the three tiers, waitlist-first access.
5. **Before beta:** move waitlist + project state off SQLite/Cloud-Run-
   ephemeral storage onto Firestore or Cloud SQL.

## 7. Success metrics

- Waitlist size and conversion to alpha usage
- Projects that reach a "finished" state (the mentor equivalent of retention)
- Weekly active mentor conversations per subscriber
- Papers/posters/fair projects citing Kairos+Janus (the long-term flywheel)

## 8. Honest risks

- **"Why not just ChatGPT?"** Answer with the integration: Janus runs the
  analyses live, sees the user's actual results, validates against ground
  truth, and remembers the whole project. A generic chatbot can do none of
  that. This answer must stay true, so the tool-integration depth is the
  moat and the roadmap priority.
- **Fabrication risk:** a mentor that invents citations is dead on arrival.
  Citation discipline is enforced in the prompt AND verified by resolving
  every DOI/arXiv ID it emits before display.
- **Scope creep:** v1 ships the mentor loop only. No figure generation, no
  manuscript writing, no LMS integrations until the loop retains users.

## 9. What YOU need to provide to turn it all on

Everything below is already wired in code; these are the inputs only you can
supply. Nothing here blocks the free early-access experience — that works the
moment the backend is deployed with the existing keys.

**Required for Janus to respond at all (already have it):**
- `OPENROUTER_API_KEY` — the same key the chat already uses. Janus reuses it.
  No new AI account needed.

**Required for the live analysis / monitoring tools (already have it):**
- The existing Google Earth Engine service-account credentials. Janus's
  run_analysis, scene-preview, validation and proactive-watch tools all ride
  the same GEE setup Kairos already uses. No new cloud project needed.

**Optional, to tune behavior (have sensible defaults):**
- `OPENALEX_MAILTO` — an email for the OpenAlex "polite pool" (faster
  literature search). Defaults to the project email.
- `FRONTEND_ORIGIN` — your deployed app URL, so reproducibility-pack links
  point at the real site instead of the placeholder.
- `JANUS_WATCH_ENABLED` (default on) and `JANUS_WATCH_INTERVAL_HOURS`
  (default 12) — the proactive-monitoring scheduler.

**Needed later, to charge money (NOT needed for early access):**
- A Stripe account + `STRIPE_SECRET_KEY` and a webhook. The tier→feature
  gates already exist (`entitlements.py`); a successful checkout just needs
  to call `store.set_tier(owner, tier)`. Until then, everyone is on the free
  "early access" tier that unlocks everything, which is exactly what you want
  for launch.

**Needed before real paid launch (not a key, a decision):**
- Move project state and the waitlist off SQLite (ephemeral on Cloud Run)
  onto Firestore or Cloud SQL. This is an afternoon of work when you're
  ready; flagged so it doesn't surprise you.

**Optional premium upgrade (money, later):**
- An ElevenLabs or OpenAI TTS key if you want studio-quality spoken replies
  instead of the free built-in browser voice. Purely a polish upgrade for
  the paid tier; the free voice already works.

In short: with the keys you already have, deploy and the entire v1+v2
experience is live and free. The only genuinely new thing you must obtain,
and only when you decide to start charging, is a Stripe account.
