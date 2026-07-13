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

### v2 — the researcher's power tools
- **Reproducibility pack:** one click exports a project's full method trail
  (every analysis, parameter, date, dataset version) as a methods-section
  draft plus a shareable Kairos case link. Reviewers can re-run everything.
- **Validation coach:** wires the user's claims to the ground-truth
  validation endpoints (IoU / precision / recall against Global Flood
  Database, MCD64A1, Hansen) and teaches what the numbers mean.
- **Writing reviewer:** critiques drafts for overclaiming, missing caveats,
  and unsupported causal language. Reviews, does not write.
- **Custom pipelines:** guided authoring of new analysis recipes (thresholds,
  bands, baselines) saved to the user's account, riding on the existing
  AnalysisRegistry pattern.

### v3 — the moat
- **Cohorts and classrooms:** teacher dashboards, assignment templates,
  team projects (school license revenue).
- **Janus-reviewed public gallery:** finished student projects published with
  reproducible links; the marketing engine and the credibility engine.
- **Cross-domain packs:** curricula and dataset bundles per field
  (public health, conservation, maritime, disaster risk).

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
